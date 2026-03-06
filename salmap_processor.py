"""
==============================================================================
SalMap Processor — Converts PAVER saliency maps to S_xyz (3D sphere coords)
==============================================================================

This is the first component of the MUSE-VP pipeline (extends STAR-VP).

WHAT IT DOES:
  PAVER outputs 2D saliency maps in equirectangular format:
    S̄ ∈ R^{H × W}   (H=224, W=448, values in [0, 1])

  The SalMap Processor converts these to 3D sphere coordinates:
    S_xyz ∈ R^{K × 3}   (K = top-K most salient 3D locations on unit sphere)

WHY:
  Head trajectory is represented as 3D unit vectors on a sphere.
  Saliency maps are 2D equirectangular images.
  To fuse them in the Spatial Attention Module (STAR-VP Section 3.4),
  they MUST be in the same coordinate space → 3D sphere.

HOW:
  1. For each pixel (i, j) in the H×W saliency map:
     - Compute longitude θ and latitude φ from equirectangular projection
     - Convert (θ, φ) to 3D unit vector (x, y, z) on unit sphere
  2. Select the top-K pixels with highest saliency values
  3. Output their 3D coordinates + saliency weights

COORDINATE CONVENTION (same as STAR-VP / standard geographic):
  θ (yaw/longitude): 0 to 2π, measured from positive Z-axis in XZ plane
  φ (pitch/latitude): -π/2 (south pole) to +π/2 (north pole)

  x = cos(φ) × sin(θ)   (points right when θ=π/2)
  y = sin(φ)             (points up when φ=π/2)
  z = cos(φ) × cos(θ)   (points forward when θ=0)

USAGE:
  # As a module (import into MUSE-VP model):
  from salmap_processor import SalMapProcessor
  processor = SalMapProcessor(top_k=32)
  s_xyz, s_weights = processor(saliency_map)   # saliency_map: [H, W] or [T, H, W]

  # As a standalone script:
  python salmap_processor.py --input path/to/saliency.pt --output path/to/output.pt
==============================================================================
"""

import math
import torch
import torch.nn as nn
import numpy as np


class SalMapProcessor(nn.Module):
    """
    Converts 2D equirectangular saliency maps to 3D sphere coordinates.
    
    This is NOT a trainable module — it's a pure geometric transformation.
    We make it an nn.Module so it can be easily integrated into PyTorch pipelines.
    
    Input:  Saliency map S̄ ∈ R^{H × W}  (single frame)
            OR batch      S̄ ∈ R^{T × H × W}  (T frames)
    
    Output: S_xyz    ∈ R^{K × 3}   (3D coordinates of top-K salient points)
            S_weight ∈ R^{K}       (saliency weights of those points)
            
            OR for batch:
            S_xyz    ∈ R^{T × K × 3}
            S_weight ∈ R^{T × K}
    """
    
    def __init__(self, top_k=32, height=224, width=448):
        """
        Args:
            top_k:  Number of most salient points to select per frame.
                    Higher K = more detail but slower attention computation.
                    Typical values: 16, 32, 64. Default: 32
            height: Height of input saliency map (from PAVER). Default: 224
            width:  Width of input saliency map (from PAVER). Default: 448
        """
        super().__init__()
        self.top_k = top_k
        self.height = height
        self.width = width
        
        # =====================================================================
        # PRE-COMPUTE the 3D sphere coordinates for ALL pixels in the saliency map.
        # This is done ONCE during initialization and reused for every frame.
        # =====================================================================
        
        # Step 1: Create pixel coordinate grids
        # i = row index (0 to H-1), j = column index (0 to W-1)
        i_coords = torch.arange(height, dtype=torch.float32)  # [H]
        j_coords = torch.arange(width, dtype=torch.float32)   # [W]
        
        # Create 2D grids: grid_i[i,j] = i, grid_j[i,j] = j
        grid_i, grid_j = torch.meshgrid(i_coords, j_coords, indexing='ij')  # [H, W] each
        
        # Step 2: Convert pixel coordinates to spherical angles
        # 
        # Equirectangular projection mapping:
        #   - Column j maps to longitude θ (yaw):
        #     θ = 2π × (j + 0.5) / W
        #     Range: [0, 2π] — full 360° horizontal sweep
        #     j=0 → θ≈0 (front), j=W/4 → θ≈π/2 (right), j=W/2 → θ≈π (back)
        #
        #   - Row i maps to latitude φ (pitch):
        #     φ = π/2 - π × (i + 0.5) / H
        #     Range: [+π/2, -π/2] — top of image is "looking up", bottom is "looking down"
        #     i=0 → φ≈+π/2 (north/up), i=H/2 → φ≈0 (equator), i=H-1 → φ≈-π/2 (south/down)
        #
        theta = 2.0 * math.pi * (grid_j + 0.5) / width    # longitude [H, W]
        phi   = math.pi / 2.0 - math.pi * (grid_i + 0.5) / height  # latitude [H, W]
        
        # Step 3: Convert spherical angles to 3D unit vectors
        #
        #   x = cos(φ) × sin(θ)
        #   y = sin(φ)
        #   z = cos(φ) × cos(θ)
        #
        # These are points on the unit sphere. Norm of (x, y, z) = 1 always.
        #
        cos_phi = torch.cos(phi)  # [H, W]
        
        x = cos_phi * torch.sin(theta)  # [H, W]
        y = torch.sin(phi)               # [H, W]
        z = cos_phi * torch.cos(theta)   # [H, W]
        
        # Stack into [H, W, 3] tensor
        sphere_coords = torch.stack([x, y, z], dim=-1)  # [H, W, 3]
        
        # Reshape to [H*W, 3] for efficient indexing later
        sphere_coords_flat = sphere_coords.reshape(-1, 3)  # [H*W, 3]
        
        # Step 4: Pre-compute latitude-based area correction weights
        #
        # In equirectangular projection, pixels near the poles represent LESS
        # actual area on the sphere than pixels at the equator.
        # Area weight = cos(φ) — corrects for this distortion.
        #
        # Without this: the model would over-represent salient regions near poles.
        # With this: each pixel's saliency is proportional to its TRUE solid angle.
        #
        area_weight = cos_phi.reshape(-1)  # [H*W]
        
        # Register as buffers (not trainable, but move with .to(device))
        self.register_buffer('sphere_coords_flat', sphere_coords_flat)
        self.register_buffer('area_weight', area_weight)
        self.register_buffer('sphere_coords', sphere_coords)
        
        print(f"[SalMapProcessor] Initialized:")
        print(f"  Input resolution: {height} × {width}")
        print(f"  Top-K salient points: {top_k}")
        print(f"  Pre-computed {height * width} sphere coordinates")
    
    def forward(self, saliency_map):
        """
        Process saliency map(s) to extract top-K 3D salient locations.
        
        Args:
            saliency_map: torch.Tensor
                Shape [H, W] for single frame
                Shape [T, H, W] for T frames (batch of frames)
                Values in [0, 1], float32
        
        Returns:
            s_xyz:    torch.Tensor — 3D coordinates of top-K salient points
                      Shape [K, 3] for single frame
                      Shape [T, K, 3] for T frames
                      
            s_weight: torch.Tensor — Saliency weights of those points
                      Shape [K] for single frame  
                      Shape [T, K] for T frames
                      Values in [0, 1], normalized so they sum to 1 per frame
        """
        # Handle single frame vs batch
        single_frame = False
        if saliency_map.dim() == 2:
            saliency_map = saliency_map.unsqueeze(0)  # [1, H, W]
            single_frame = True
        
        T, H, W = saliency_map.shape
        assert H == self.height and W == self.width, \
            f"Expected saliency map of size {self.height}×{self.width}, got {H}×{W}"
        
        K = self.top_k
        
        # =====================================================================
        # STEP 1: Apply area correction
        # =====================================================================
        # Multiply saliency by cos(φ) to correct for equirectangular distortion.
        # This ensures we don't over-select salient points near the poles.
        #
        # corrected_sal[i,j] = saliency[i,j] × cos(latitude_of_pixel_ij)
        #
        sal_flat = saliency_map.reshape(T, -1)  # [T, H*W]
        corrected_sal = sal_flat * self.area_weight.unsqueeze(0)  # [T, H*W]
        
        # =====================================================================
        # STEP 2: Select top-K most salient pixels per frame
        # =====================================================================
        # torch.topk returns the K largest values and their indices
        #
        # top_values: [T, K] — the saliency values of the top-K pixels
        # top_indices: [T, K] — the flat indices (0 to H*W-1) of those pixels
        #
        top_values, top_indices = torch.topk(corrected_sal, k=K, dim=1)  # [T, K]
        
        # =====================================================================
        # STEP 3: Look up the 3D sphere coordinates for those pixels
        # =====================================================================
        # sphere_coords_flat[index] gives the (x, y, z) for pixel at flat index
        #
        # We need to gather coordinates for each frame's top-K indices.
        # Expand indices to [T, K, 3] for gathering from [H*W, 3]
        #
        # For each frame t and each top-k index k:
        #   s_xyz[t, k, :] = sphere_coords_flat[top_indices[t, k], :]
        #
        coords = self.sphere_coords_flat  # [H*W, 3]
        
        # Gather: index into the first dimension of coords using top_indices
        # top_indices: [T, K] → expand to [T, K, 3]
        idx_expanded = top_indices.unsqueeze(-1).expand(-1, -1, 3)  # [T, K, 3]
        
        # Expand coords to [T, H*W, 3] then gather along dim=1
        coords_expanded = coords.unsqueeze(0).expand(T, -1, -1)  # [T, H*W, 3]
        s_xyz = torch.gather(coords_expanded, dim=1, index=idx_expanded)  # [T, K, 3]
        
        # =====================================================================
        # STEP 4: Normalize saliency weights so they sum to 1 per frame
        # =====================================================================
        # This makes the weights interpretable as a probability distribution
        # over the top-K salient locations.
        #
        # If all saliency values are 0 (blank frame), use uniform weights.
        #
        weight_sum = top_values.sum(dim=1, keepdim=True)  # [T, 1]
        weight_sum = weight_sum.clamp(min=1e-8)  # avoid division by zero
        s_weight = top_values / weight_sum  # [T, K], sums to 1 per frame
        
        # Remove batch dimension if input was single frame
        if single_frame:
            s_xyz = s_xyz.squeeze(0)      # [K, 3]
            s_weight = s_weight.squeeze(0) # [K]
        
        return s_xyz, s_weight
    
    def process_full_video(self, saliency_tensor, chunk_size=500, verbose=True):
        """
        Process an entire video's saliency maps efficiently in chunks.
        
        Avoids loading all frames into GPU at once — processes in chunks 
        and concatenates results on CPU.
        
        Args:
            saliency_tensor: torch.Tensor [num_frames, H, W]
                Full video saliency from PAVER (loaded from _saliency.pt file)
            chunk_size: int
                Number of frames to process at once. Default: 500
            verbose: bool
                Print progress. Default: True
                
        Returns:
            s_xyz:    torch.Tensor [num_frames, K, 3] — 3D coordinates (CPU)
            s_weight: torch.Tensor [num_frames, K]    — saliency weights (CPU)
        """
        num_frames = saliency_tensor.shape[0]
        
        if verbose:
            print(f"  Processing {num_frames} frames in chunks of {chunk_size}...")
        
        all_xyz = []
        all_weights = []
        
        for start in range(0, num_frames, chunk_size):
            end = min(start + chunk_size, num_frames)
            chunk = saliency_tensor[start:end]  # [chunk, H, W]
            
            # Move chunk to same device as the pre-computed coords
            device = self.sphere_coords_flat.device
            chunk = chunk.to(device)
            
            # Process chunk
            with torch.no_grad():
                xyz, weight = self.forward(chunk)
            
            # Store on CPU to save memory
            all_xyz.append(xyz.cpu())
            all_weights.append(weight.cpu())
            
            if verbose and (start // chunk_size) % 10 == 0:
                progress = end / num_frames * 100
                print(f"    Progress: {end}/{num_frames} frames ({progress:.1f}%)")
        
        # Concatenate all chunks
        s_xyz = torch.cat(all_xyz, dim=0)      # [num_frames, K, 3]
        s_weight = torch.cat(all_weights, dim=0) # [num_frames, K]
        
        if verbose:
            print(f"  ✓ Done: s_xyz shape = {s_xyz.shape}, s_weight shape = {s_weight.shape}")
        
        return s_xyz, s_weight


def process_single_video(input_path, output_path, top_k=32, device='cpu'):
    """
    Process a single video's saliency .pt file through the SalMap Processor.
    
    Args:
        input_path:  Path to PAVER saliency .pt file  (e.g., 'video_saliency.pt')
        output_path: Path to save processed S_xyz .pt file
        top_k:       Number of top salient points per frame
        device:      'cpu' or 'cuda' — use 'cpu' if GPU memory is limited
    
    Saves a dictionary to output_path:
        {
            's_xyz':    tensor [num_frames, K, 3],   # 3D coordinates
            's_weight': tensor [num_frames, K],       # saliency weights  
            'top_k':    int,                          # K value used
            'input_shape': tuple,                     # original (num_frames, H, W)
            'source_file': str                        # path to source saliency file
        }
    """
    import os
    
    print(f"\n{'='*70}")
    print(f"SalMap Processor — Processing: {os.path.basename(input_path)}")
    print(f"{'='*70}")
    
    # Step 1: Load PAVER saliency tensor
    print(f"\n[1/3] Loading saliency map from: {input_path}")
    saliency = torch.load(input_path, map_location='cpu', weights_only=True)
    print(f"  Shape: {saliency.shape}  (num_frames={saliency.shape[0]}, "
          f"H={saliency.shape[1]}, W={saliency.shape[2]})")
    print(f"  Dtype: {saliency.dtype}, Range: [{saliency.min():.4f}, {saliency.max():.4f}]")
    
    # Step 2: Initialize SalMap Processor
    print(f"\n[2/3] Initializing SalMap Processor (top_k={top_k})...")
    processor = SalMapProcessor(
        top_k=top_k,
        height=saliency.shape[1],
        width=saliency.shape[2]
    )
    processor = processor.to(device)
    
    # Step 3: Process all frames
    print(f"\n[3/3] Processing all frames...")
    s_xyz, s_weight = processor.process_full_video(
        saliency, 
        chunk_size=500,
        verbose=True
    )
    
    # Step 4: Save results
    output_dict = {
        's_xyz':       s_xyz,                           # [num_frames, K, 3]
        's_weight':    s_weight,                         # [num_frames, K]
        'top_k':       top_k,
        'input_shape': tuple(saliency.shape),            # (num_frames, H, W)
        'source_file': str(input_path)
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    torch.save(output_dict, output_path)
    
    # Step 5: Print summary
    print(f"\n{'='*70}")
    print(f"SAVED: {output_path}")
    print(f"{'='*70}")
    print(f"  s_xyz shape:    {s_xyz.shape}   (num_frames × K × 3)")
    print(f"  s_weight shape: {s_weight.shape}   (num_frames × K)")
    print(f"  s_xyz range:    [{s_xyz.min():.4f}, {s_xyz.max():.4f}]")
    print(f"  s_weight sum:   {s_weight[0].sum():.4f} (should be ~1.0 per frame)")
    print(f"  File size:      {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    
    # Quick sanity check: verify unit vectors
    norms = torch.norm(s_xyz, dim=-1)  # should all be ~1.0
    print(f"  Norm check:     min={norms.min():.6f}, max={norms.max():.6f} (should be ~1.0)")
    
    return s_xyz, s_weight


def process_all_videos(saliency_dir, output_dir, top_k=32, device='cpu'):
    """
    Process ALL saliency .pt files in a directory.
    
    Args:
        saliency_dir: Directory containing *_saliency.pt files (e.g., PAVER/code/qual/)
        output_dir:   Directory to save processed *_salxyz.pt files
        top_k:        Number of top salient points per frame
        device:       'cpu' or 'cuda'
    
    Creates one *_salxyz.pt file for each *_saliency.pt file.
    """
    import os
    import glob
    import time
    
    # Find all saliency files
    pattern = os.path.join(saliency_dir, '*_saliency.pt')
    saliency_files = sorted(glob.glob(pattern))
    
    if len(saliency_files) == 0:
        print(f"ERROR: No *_saliency.pt files found in {saliency_dir}")
        return
    
    print(f"\n{'#'*70}")
    print(f"BATCH SalMap Processor — Processing {len(saliency_files)} videos")
    print(f"{'#'*70}")
    print(f"  Input directory:  {saliency_dir}")
    print(f"  Output directory: {output_dir}")
    print(f"  Top-K: {top_k}")
    print(f"  Device: {device}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    total_start = time.time()
    results = []
    
    for idx, sal_path in enumerate(saliency_files):
        video_name = os.path.basename(sal_path).replace('_saliency.pt', '')
        output_path = os.path.join(output_dir, f'{video_name}_salxyz.pt')
        
        # Skip if already processed
        if os.path.exists(output_path):
            print(f"\n[{idx+1}/{len(saliency_files)}] SKIP (already exists): {video_name}")
            results.append((video_name, "skipped"))
            continue
        
        print(f"\n[{idx+1}/{len(saliency_files)}] Processing: {video_name}")
        
        start = time.time()
        try:
            s_xyz, s_weight = process_single_video(
                input_path=sal_path,
                output_path=output_path,
                top_k=top_k,
                device=device
            )
            elapsed = time.time() - start
            results.append((video_name, f"OK ({elapsed:.1f}s)"))
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR: {e}")
            results.append((video_name, f"FAILED: {e}"))
    
    # Print final summary
    total_elapsed = time.time() - total_start
    print(f"\n\n{'#'*70}")
    print(f"BATCH COMPLETE — Total time: {total_elapsed:.1f}s")
    print(f"{'#'*70}")
    for name, status in results:
        print(f"  {name}: {status}")
    
    # List output files
    output_files = sorted(glob.glob(os.path.join(output_dir, '*_salxyz.pt')))
    print(f"\nOutput files ({len(output_files)}):")
    for f in output_files:
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f"  {os.path.basename(f)} ({size_mb:.1f} MB)")


def inspect_salxyz(filepath):
    """
    Inspect a processed S_xyz file — useful for debugging and visualization.
    
    Args:
        filepath: Path to *_salxyz.pt file
    """
    import os
    
    print(f"\n{'='*70}")
    print(f"Inspecting: {os.path.basename(filepath)}")
    print(f"{'='*70}")
    
    data = torch.load(filepath, map_location='cpu', weights_only=False)
    
    s_xyz = data['s_xyz']
    s_weight = data['s_weight']
    
    print(f"  Source:        {data['source_file']}")
    print(f"  Input shape:   {data['input_shape']}")
    print(f"  Top-K:         {data['top_k']}")
    print(f"  s_xyz shape:   {s_xyz.shape}")
    print(f"  s_weight shape:{s_weight.shape}")
    print(f"  s_xyz dtype:   {s_xyz.dtype}")
    print(f"  s_xyz range:   x=[{s_xyz[...,0].min():.4f}, {s_xyz[...,0].max():.4f}]")
    print(f"                 y=[{s_xyz[...,1].min():.4f}, {s_xyz[...,1].max():.4f}]")
    print(f"                 z=[{s_xyz[...,2].min():.4f}, {s_xyz[...,2].max():.4f}]")
    
    norms = torch.norm(s_xyz, dim=-1)
    print(f"  Norms:         min={norms.min():.6f}, max={norms.max():.6f}")
    print(f"  Weight sum:    frame0={s_weight[0].sum():.6f}, "
          f"frame_last={s_weight[-1].sum():.6f}")
    
    # Show sample: first frame's top-5 salient points
    print(f"\n  Sample — Frame 0, Top-5 most salient 3D points:")
    print(f"  {'Rank':<6} {'x':>8} {'y':>8} {'z':>8} {'weight':>8}")
    for k in range(min(5, s_xyz.shape[1])):
        x, y, z = s_xyz[0, k]
        w = s_weight[0, k]
        # Convert back to yaw/pitch for readability
        yaw_deg = math.degrees(math.atan2(x.item(), z.item()))
        pitch_deg = math.degrees(math.asin(max(-1, min(1, y.item()))))
        print(f"  {k+1:<6} {x:>8.4f} {y:>8.4f} {z:>8.4f} {w:>8.4f}  "
              f"(yaw={yaw_deg:>7.2f}°, pitch={pitch_deg:>7.2f}°)")


# ==============================================================================
# COMMAND-LINE INTERFACE
# ==============================================================================

if __name__ == '__main__':
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description='SalMap Processor — Convert PAVER saliency maps to S_xyz (3D sphere coords)',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
EXAMPLES:
  # Process a single video:
  python salmap_processor.py --input qual/exp2_video_04_Female_Basketball_Match_saliency.pt --output salxyz/exp2_video_04_salxyz.pt
  
  # Process ALL videos in a directory:
  python salmap_processor.py --batch --input-dir ../PAVER/code/qual --output-dir salxyz/
  
  # Inspect a processed file:
  python salmap_processor.py --inspect salxyz/exp2_video_04_salxyz.pt
  
  # Use GPU for faster processing:
  python salmap_processor.py --batch --input-dir ../PAVER/code/qual --output-dir salxyz/ --device cuda
        """
    )
    
    # Mode selection
    parser.add_argument('--batch', action='store_true',
                        help='Process ALL saliency files in --input-dir')
    parser.add_argument('--inspect', type=str, default=None,
                        help='Inspect an already-processed _salxyz.pt file')
    
    # Single video mode
    parser.add_argument('--input', type=str, default=None,
                        help='Path to a single *_saliency.pt file')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to save the output *_salxyz.pt file')
    
    # Batch mode
    parser.add_argument('--input-dir', type=str, 
                        default='/media/user/HDD3/Shini/STAR_VP/PAVER/code/qual',
                        help='Directory containing *_saliency.pt files')
    parser.add_argument('--output-dir', type=str,
                        default='/media/user/HDD3/Shini/STAR_VP/muse_vp/salxyz',
                        help='Directory to save *_salxyz.pt files')
    
    # Parameters
    parser.add_argument('--top-k', type=int, default=32,
                        help='Number of top salient points per frame (default: 32)')
    parser.add_argument('--device', type=str, default='cpu',
                        choices=['cpu', 'cuda'],
                        help='Device to use (default: cpu — fast enough for this)')
    
    args = parser.parse_args()
    
    # Mode: Inspect
    if args.inspect:
        inspect_salxyz(args.inspect)
    
    # Mode: Batch
    elif args.batch:
        process_all_videos(
            saliency_dir=args.input_dir,
            output_dir=args.output_dir,
            top_k=args.top_k,
            device=args.device
        )
    
    # Mode: Single video
    elif args.input:
        if args.output is None:
            # Auto-generate output path
            base = os.path.basename(args.input).replace('_saliency.pt', '_salxyz.pt')
            os.makedirs(args.output_dir, exist_ok=True)
            args.output = os.path.join(args.output_dir, base)
        
        process_single_video(
            input_path=args.input,
            output_path=args.output,
            top_k=args.top_k,
            device=args.device
        )
    
    else:
        parser.print_help()
        print("\nERROR: Specify --batch, --inspect, or --input. See examples above.")
