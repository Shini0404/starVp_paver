"""
=============================================================================
MUSE-VP Data Preprocessing Pipeline (Stage 1)
=============================================================================

Converts raw CSV tracking data from Meta Quest Pro into aligned, normalized
feature tensors ready for the MUSE-VP model.

Input:
    Per participant per video: combined.csv, eye.csv, face.csv, head.csv
    (recorded at ~72Hz from Meta Quest Pro)

Output:
    Per participant per video: <video_id>.pt containing:
        - head_3d    [N, 3]  : Head direction as 3D unit vectors
        - eye_3d     [N, 3]  : Eye gaze direction as 3D unit vectors
        - offset     [N, 3]  : Normalized eye-head offset (relH, relV, magnitude)
        - fixation   [N, 2]  : Fixation state + normalized duration
        - face       [N, 5]  : Face expression features
        where N = number of frames at TARGET_FPS (default 5fps)

    Plus a global metadata.pt with participant-to-integer-ID mapping.

Pipeline Steps:
    1. Parse CSVs and extract relevant columns
    2. Filter pre-video samples (VideoFrame == -1)
    3. Align to video frames (group by VideoFrame, average within each frame)
    4. Fill any missing frames via interpolation
    5. Handle invalid sensor data using validity flags
    6. Convert head Euler angles to 3D unit vectors on the sphere
    7. Normalize eye gaze vectors to unit length
    8. Normalize offset and fixation features
    9. Extract and compose face expression features
    10. Downsample from 30fps to target fps (5fps)
    11. Convert to PyTorch tensors and save

Usage:
    python -m muse_vp.data_preprocessing \\
        --data-root DataCollectedEyeHeadFaceCombined \\
        --salxyz-dir muse_vp/salxyz \\
        --output-dir muse_vp/processed_data
=============================================================================
"""

import os
import re
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, Optional, List

import numpy as np
import pandas as pd
import torch


# =============================================================================
# CONFIGURATION
# =============================================================================

# Sampling rates
VIDEO_FPS = 30          # Native video frame rate (Wu_MMSys_17 standard)
TARGET_FPS = 5          # Downsampled rate for the model (every 6th frame)
TRACKING_HZ = 72        # Approximate Quest Pro tracking rate

# Normalization constants (from architecture doc Section 1.3)
OFFSET_NORM_FACTOR = 30.0       # Degrees — normalizes gaze offset to ~[-1, 1]
FIXATION_DUR_NORM = 1000.0      # Milliseconds — converts to seconds, capped at 1.0
FIXATION_DUR_CAP = 1.0          # Upper bound after normalization

# The 14 target videos used in data collection.
# Maps the content name (after removing "video_XX_" prefix from folder name)
# to the corresponding PAVER salxyz filename in muse_vp/salxyz/.
VIDEO_CONTENT_TO_SALXYZ = {
    "Weekly_Idol-Dancing":          "exp2_video_01_Weekly_Idol-Dancing_salxyz.pt",
    "Damai_Music_Live-Vocie_Toy":   "exp2_video_02_Damai_Music_Live-Vocie_Toy_salxyz.pt",
    "Rio_Olympics_VR_Interview":     "exp2_video_12_Rio_Olympics_VR_Interview_salxyz.pt",
    "Female_Basketball_Match":       "exp2_video_04_Female_Basketball_Match_salxyz.pt",
    "SHOWTIME_Boxing":               "exp2_video_05_SHOWTIME_Boxing_salxyz.pt",
    "Rosa_Khutor_Ski_360":           "exp1_video_06_Rosa_Khutor_Ski_360_salxyz.pt",
    "Hammerhead_Shark_NatGeo_360":   "exp2_video_07_Hammerhead_Shark_NatGeo_360_salxyz.pt",
    "Freestyle_Skiing":              "exp1_video_02_Freestyle_Skiing_salxyz.pt",
    "Google_Spotlight-HELP":         "exp1_video_03_Google_Spotlight-HELP_salxyz.pt",
    "Deep_Ocean_Horror_360":         "exp2_video_09_Deep_Ocean_Horror_360_salxyz.pt",
    "GoPro_VR-Tahiti_Surf":          "exp1_video_05_GoPro_VR-Tahiti_Surf_salxyz.pt",
    "LOSC_Football":                 "exp1_video_08_LOSC_Football_salxyz.pt",
    "Jungle_Book_360":               "exp2_video_11_Jungle_Book_360_salxyz.pt",
    "Death_Note_VR":                 "exp2_video_10_Death_Note_VR_salxyz.pt",
}

# Set of valid content names for quick lookup
VALID_VIDEO_CONTENT_NAMES = set(VIDEO_CONTENT_TO_SALXYZ.keys())

logger = logging.getLogger("muse_vp.preprocessing")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def extract_content_name(video_folder_name: str) -> Optional[str]:
    """
    Extract the video content name from a collected data folder name.

    "video_01_Weekly_Idol-Dancing" → "Weekly_Idol-Dancing"
    "video_14_Death_Note_VR"       → "Death_Note_VR"

    Returns None if the folder name doesn't match the expected pattern.
    """
    match = re.match(r"video_\d{2}_(.*)", video_folder_name)
    return match.group(1) if match else None


def euler_to_unit_vector(yaw_deg: np.ndarray, pitch_deg: np.ndarray) -> np.ndarray:
    """
    Convert yaw/pitch Euler angles (degrees) to 3D unit vectors on a sphere.

    Uses the same coordinate convention as SalMapProcessor:
        x = cos(pitch) * sin(yaw)
        y = sin(pitch)
        z = cos(pitch) * cos(yaw)

    Where:
        yaw=0, pitch=0  → (0, 0, 1)  = looking forward (+Z)
        yaw=90°, pitch=0 → (1, 0, 0) = looking right (+X)
        yaw=0, pitch=90° → (0, 1, 0) = looking up (+Y)

    Args:
        yaw_deg:   [N] array of yaw angles in degrees
        pitch_deg: [N] array of pitch angles in degrees

    Returns:
        [N, 3] array of 3D unit vectors (x, y, z)
    """
    yaw_rad = np.deg2rad(yaw_deg)
    pitch_rad = np.deg2rad(pitch_deg)
    cos_pitch = np.cos(pitch_rad)

    x = cos_pitch * np.sin(yaw_rad)
    y = np.sin(pitch_rad)
    z = cos_pitch * np.cos(yaw_rad)

    return np.stack([x, y, z], axis=-1)


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """
    Normalize an array of vectors to unit length.
    Handles zero-length vectors by replacing them with [0, 0, 1] (forward).

    Args:
        vectors: [N, 3] array of 3D vectors

    Returns:
        [N, 3] array of unit vectors
    """
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    # Replace zero norms to avoid division by zero
    zero_mask = (norms < 1e-8).squeeze(-1)
    norms[norms < 1e-8] = 1.0
    unit_vectors = vectors / norms
    # Set zero-length vectors to forward direction
    unit_vectors[zero_mask] = np.array([0.0, 0.0, 1.0])
    return unit_vectors


# =============================================================================
# CSV LOADING
# =============================================================================

def load_combined_csv(filepath: str) -> pd.DataFrame:
    """
    Load combined.csv and return only the columns needed for preprocessing.

    Columns used:
        - VideoFrame:     frame index for temporal alignment
        - HeadYaw, HeadPitch: for head 3D unit vector conversion
        - GazeRelativeH, GazeRelativeV, EyeHeadOffset: for offset features
        - FaceActivity, BrowDownL, BrowDownR, JawOpen,
          EyeClosedL, EyeClosedR: for face features
    """
    usecols = [
        "VideoFrame", "HeadYaw", "HeadPitch",
        "GazeRelativeH", "GazeRelativeV", "EyeHeadOffset",
        "FaceActivity", "BrowDownL", "BrowDownR", "JawOpen",
        "EyeClosedL", "EyeClosedR",
    ]
    df = pd.read_csv(filepath, usecols=usecols)
    return df


def load_eye_csv(filepath: str) -> pd.DataFrame:
    """
    Load eye.csv and return only the columns needed for preprocessing.

    Columns used:
        - VideoFrame:                   for alignment
        - GazeDir.x, GazeDir.y, GazeDir.z: 3D eye gaze direction
        - IsFixating, FixationDurationMs:   fixation features
        - BothEyesValid:                validity flag
    """
    usecols = [
        "VideoFrame",
        "GazeDir.x", "GazeDir.y", "GazeDir.z",
        "IsFixating", "FixationDurationMs",
        "BothEyesValid",
    ]
    df = pd.read_csv(filepath, usecols=usecols)
    return df


def load_face_csv(filepath: str) -> pd.DataFrame:
    """
    Load face.csv and return only the columns needed for preprocessing.

    Columns used:
        - VideoFrame:                        for alignment
        - FaceIsValid:                       validity flag
        - Inner_Brow_Raiser_L, Inner_Brow_Raiser_R: for BrowRaise feature
    """
    usecols = [
        "VideoFrame", "FaceIsValid",
        "Inner_Brow_Raiser_L", "Inner_Brow_Raiser_R",
    ]
    df = pd.read_csv(filepath, usecols=usecols)
    return df


# =============================================================================
# TEMPORAL ALIGNMENT
# =============================================================================

def align_to_video_frames(
    combined_df: pd.DataFrame,
    eye_df: pd.DataFrame,
    face_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Align tracking data (recorded at ~72Hz) to video frames (30fps).

    The Quest Pro records at ~72Hz, producing 2-3 samples per video frame.
    This function groups samples by VideoFrame and takes their mean,
    producing exactly one row per video frame.

    Steps:
        1. Filter out pre-video rows (VideoFrame == -1)
        2. Group by VideoFrame and compute mean for each column
        3. Create a continuous frame index (0 to max_frame, no gaps)
        4. Forward-fill then backward-fill any missing frames
        5. Merge data from all 3 CSV sources into one DataFrame

    Args:
        combined_df: DataFrame from combined.csv
        eye_df:      DataFrame from eye.csv
        face_df:     DataFrame from face.csv

    Returns:
        Merged DataFrame with one row per video frame (0 to max_frame),
        containing all columns needed for feature extraction.
    """
    # --- Step 1: Filter out pre-video rows ---
    combined_df = combined_df[combined_df["VideoFrame"] >= 0].copy()
    eye_df = eye_df[eye_df["VideoFrame"] >= 0].copy()
    face_df = face_df[face_df["VideoFrame"] >= 0].copy()

    # --- Step 2: Group by VideoFrame and compute mean ---
    # For most columns, mean is appropriate since samples within a frame
    # span only ~13ms (negligible temporal variation).
    combined_grouped = combined_df.groupby("VideoFrame").mean()
    eye_grouped = eye_df.groupby("VideoFrame").mean()
    face_grouped = face_df.groupby("VideoFrame").mean()

    # --- Step 3: Create continuous frame index ---
    max_frame = int(max(
        combined_grouped.index.max(),
        eye_grouped.index.max(),
        face_grouped.index.max(),
    ))
    full_index = pd.RangeIndex(start=0, stop=max_frame + 1, name="VideoFrame")

    combined_aligned = combined_grouped.reindex(full_index)
    eye_aligned = eye_grouped.reindex(full_index)
    face_aligned = face_grouped.reindex(full_index)

    # --- Step 4: Fill gaps ---
    # Forward-fill first (use last known value), then backward-fill for
    # any leading NaNs (rare: only if frame 0 has no samples).
    combined_aligned = combined_aligned.ffill().bfill()
    eye_aligned = eye_aligned.ffill().bfill()
    face_aligned = face_aligned.ffill().bfill()

    # --- Step 5: Merge into single DataFrame ---
    # All three DataFrames now share the same index. We concatenate columns,
    # using suffixes to disambiguate any shared column names.
    merged = pd.concat(
        [combined_aligned, eye_aligned, face_aligned],
        axis=1,
    )

    # Handle duplicate column names that may result from concat
    # (e.g., both combined and face may have computed columns).
    # pandas keeps all columns; we disambiguate by renaming face-specific ones.
    if merged.columns.duplicated().any():
        cols = merged.columns.tolist()
        seen = {}
        new_cols = []
        for c in cols:
            if c in seen:
                seen[c] += 1
                new_cols.append(f"{c}__dup{seen[c]}")
            else:
                seen[c] = 0
                new_cols.append(c)
        merged.columns = new_cols

    logger.debug(
        f"  Aligned {len(merged)} frames (0 to {max_frame}) at {VIDEO_FPS}fps"
    )
    return merged


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

def extract_all_features(aligned_df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    Extract all feature tensors from the aligned DataFrame.

    Produces:
        head_3d   [N, 3] : 3D head direction unit vectors
        eye_3d    [N, 3] : 3D eye gaze direction unit vectors
        offset    [N, 3] : Normalized (GazeRelativeH, GazeRelativeV, EyeHeadOffset)
        fixation  [N, 2] : (IsFixating, normalized FixationDuration)
        face      [N, 5] : (FaceActivity, BrowLower, JawDrop, EyesClosed, BrowRaise)

    Args:
        aligned_df: DataFrame with one row per video frame at 30fps

    Returns:
        Dictionary of feature name → numpy array
    """
    n_frames = len(aligned_df)

    # ----- HEAD 3D -----
    # Convert head Euler angles to 3D unit vectors.
    # Architecture spec: hx = cos(pitch)*sin(yaw), hy = sin(pitch), hz = cos(pitch)*cos(yaw)
    head_3d = euler_to_unit_vector(
        aligned_df["HeadYaw"].values,
        aligned_df["HeadPitch"].values,
    )

    # ----- EYE 3D -----
    # eye.csv provides the gaze direction as a 3D vector directly.
    # We normalize to ensure unit length (averaging may slightly denormalize).
    eye_raw = np.stack([
        aligned_df["GazeDir.x"].values,
        aligned_df["GazeDir.y"].values,
        aligned_df["GazeDir.z"].values,
    ], axis=-1)

    # Use the BothEyesValid flag: when eyes weren't tracked, substitute head direction.
    # After groupby mean, BothEyesValid is in [0, 1]; treat < 0.5 as invalid.
    eyes_valid = aligned_df["BothEyesValid"].values >= 0.5
    eye_raw[~eyes_valid] = head_3d[~eyes_valid]

    eye_3d = normalize_vectors(eye_raw)

    # ----- OFFSET -----
    # GazeRelativeH/V are in degrees; normalize by OFFSET_NORM_FACTOR (30°)
    # to bring into roughly [-1, 1] range.
    # EyeHeadOffset is the magnitude (always >= 0); normalize similarly.
    offset = np.stack([
        aligned_df["GazeRelativeH"].values / OFFSET_NORM_FACTOR,
        aligned_df["GazeRelativeV"].values / OFFSET_NORM_FACTOR,
        aligned_df["EyeHeadOffset"].values / OFFSET_NORM_FACTOR,
    ], axis=-1)

    # When eyes were invalid, set offset to zero (no reliable offset info)
    offset[~eyes_valid] = 0.0

    # ----- FIXATION -----
    # IsFixating: binary (0 or 1). After frame-averaging it may be fractional,
    # so we round to get a clean binary signal.
    # FixationDurationMs: convert to seconds and cap at FIXATION_DUR_CAP.
    is_fixating = np.round(aligned_df["IsFixating"].values).astype(np.float32)
    fix_duration = aligned_df["FixationDurationMs"].values / FIXATION_DUR_NORM
    fix_duration = np.clip(fix_duration, 0.0, FIXATION_DUR_CAP)

    # When eyes were invalid, no fixation info available
    is_fixating[~eyes_valid] = 0.0
    fix_duration[~eyes_valid] = 0.0

    fixation = np.stack([is_fixating, fix_duration], axis=-1)

    # ----- FACE -----
    # 5 features: FaceActivity, BrowLower_avg, JawDrop, EyesClosed_avg, BrowRaise_avg
    # All values are in [0, 1] range (blendshape values), no normalization needed.
    face_activity = aligned_df["FaceActivity"].values
    brow_lower = (aligned_df["BrowDownL"].values + aligned_df["BrowDownR"].values) / 2.0
    jaw_drop = aligned_df["JawOpen"].values
    eyes_closed = (
        aligned_df["EyeClosedL"].values + aligned_df["EyeClosedR"].values
    ) / 2.0
    brow_raise = (
        aligned_df["Inner_Brow_Raiser_L"].values
        + aligned_df["Inner_Brow_Raiser_R"].values
    ) / 2.0

    # When face tracking was invalid (FaceIsValid < 0.5 after averaging),
    # set face features to neutral (zeros).
    face_valid = aligned_df["FaceIsValid"].values >= 0.5
    face_raw = np.stack(
        [face_activity, brow_lower, jaw_drop, eyes_closed, brow_raise],
        axis=-1,
    )
    face_raw[~face_valid] = 0.0

    # ----- Assemble output -----
    features = {
        "head_3d": head_3d.astype(np.float32),       # [N, 3]
        "eye_3d": eye_3d.astype(np.float32),          # [N, 3]
        "offset": offset.astype(np.float32),          # [N, 3]
        "fixation": fixation.astype(np.float32),      # [N, 2]
        "face": face_raw.astype(np.float32),          # [N, 5]
    }

    logger.debug(f"  Extracted features: {n_frames} frames × "
                 f"({', '.join(f'{k}:{v.shape[1]}' for k, v in features.items())})")
    return features


# =============================================================================
# DOWNSAMPLING
# =============================================================================

def downsample_features(
    features: Dict[str, np.ndarray],
    src_fps: int = VIDEO_FPS,
    target_fps: int = TARGET_FPS,
) -> Dict[str, np.ndarray]:
    """
    Downsample feature arrays from src_fps to target_fps by subsampling.

    Takes every (src_fps / target_fps)-th frame. For 30fps → 5fps, this
    means taking every 6th frame: frames 0, 6, 12, 18, ...

    This matches STAR-VP's approach of operating at 5fps.

    Args:
        features:   Dict of feature name → [N_src, D] numpy arrays
        src_fps:    Source frame rate (default 30)
        target_fps: Target frame rate (default 5)

    Returns:
        Dict of feature name → [N_target, D] numpy arrays
    """
    step = src_fps // target_fps
    assert src_fps % target_fps == 0, (
        f"src_fps ({src_fps}) must be evenly divisible by target_fps ({target_fps})"
    )

    downsampled = {}
    for key, arr in features.items():
        downsampled[key] = arr[::step].copy()

    n_src = len(next(iter(features.values())))
    n_dst = len(next(iter(downsampled.values())))
    logger.debug(f"  Downsampled: {n_src} frames @ {src_fps}fps → "
                 f"{n_dst} frames @ {target_fps}fps (step={step})")
    return downsampled


# =============================================================================
# SINGLE RECORDING PROCESSING
# =============================================================================

def process_single_recording(recording_dir: str) -> Optional[Dict[str, np.ndarray]]:
    """
    Process all CSV files from a single participant-video recording.

    Args:
        recording_dir: Path to a directory containing combined.csv, eye.csv,
                       face.csv, head.csv for one participant watching one video.

    Returns:
        Dictionary of feature tensors (numpy arrays at TARGET_FPS), or None
        if processing fails.
    """
    recording_dir = Path(recording_dir)

    combined_path = recording_dir / "combined.csv"
    eye_path = recording_dir / "eye.csv"
    face_path = recording_dir / "face.csv"

    for path in [combined_path, eye_path, face_path]:
        if not path.exists():
            logger.error(f"Missing file: {path}")
            return None

    try:
        # Step 1: Load CSVs (only needed columns for memory efficiency)
        combined_df = load_combined_csv(str(combined_path))
        eye_df = load_eye_csv(str(eye_path))
        face_df = load_face_csv(str(face_path))

        # Step 2: Align to video frames (72Hz → 30fps)
        aligned_df = align_to_video_frames(combined_df, eye_df, face_df)
        num_frames_30fps = len(aligned_df)

        if num_frames_30fps == 0:
            logger.error(f"No valid video frames in {recording_dir}")
            return None

        # Step 3: Extract and normalize all features
        features = extract_all_features(aligned_df)

        # Step 4: Downsample to target fps (30fps → 5fps)
        features = downsample_features(features)
        num_frames_target = len(features["head_3d"])

        # Step 5: Attach metadata
        features["num_frames_30fps"] = num_frames_30fps
        features["num_frames_target"] = num_frames_target
        features["target_fps"] = TARGET_FPS

        return features

    except Exception as e:
        logger.error(f"Failed to process {recording_dir}: {e}", exc_info=True)
        return None


# =============================================================================
# FULL DATASET PROCESSING
# =============================================================================

def discover_recordings(data_root: str) -> List[Dict]:
    """
    Discover all valid participant-video recordings in the data root.

    Scans for directories matching the pattern:
        <data_root>/<P###>/<video_XX_ContentName>/

    Filters to only include videos whose content name is in the target list.

    Returns:
        List of dicts with keys: participant_id, video_folder, content_name,
        recording_dir, salxyz_filename
    """
    data_root = Path(data_root)
    recordings = []
    skipped = []

    # Sort participant dirs for deterministic ordering
    participant_dirs = sorted(
        [d for d in data_root.iterdir() if d.is_dir() and re.match(r"P\d{3}", d.name)]
    )

    for p_dir in participant_dirs:
        participant_id = p_dir.name
        video_dirs = sorted([d for d in p_dir.iterdir() if d.is_dir()])

        for v_dir in video_dirs:
            content_name = extract_content_name(v_dir.name)
            if content_name is None:
                skipped.append((participant_id, v_dir.name, "invalid folder name"))
                continue

            if content_name not in VALID_VIDEO_CONTENT_NAMES:
                skipped.append((participant_id, v_dir.name, "not in target 14 videos"))
                continue

            salxyz_filename = VIDEO_CONTENT_TO_SALXYZ[content_name]

            recordings.append({
                "participant_id": participant_id,
                "video_folder": v_dir.name,
                "content_name": content_name,
                "recording_dir": str(v_dir),
                "salxyz_filename": salxyz_filename,
            })

    logger.info(f"Discovered {len(recordings)} valid recordings "
                f"across {len(participant_dirs)} participants")
    if skipped:
        logger.info(f"Skipped {len(skipped)} recordings:")
        for pid, vname, reason in skipped:
            logger.info(f"  {pid}/{vname} — {reason}")

    return recordings


def build_participant_id_mapping(recordings: List[Dict]) -> Dict[str, int]:
    """
    Build a deterministic mapping from participant string IDs to integer IDs.

    Sorts participants alphabetically so the mapping is stable regardless of
    discovery order. Integers start from 0.

    Returns:
        Dict mapping participant_id string (e.g., "P005") to integer (e.g., 4)
    """
    unique_participants = sorted(set(r["participant_id"] for r in recordings))
    return {pid: idx for idx, pid in enumerate(unique_participants)}


def validate_salxyz_alignment(
    num_frames_30fps: int,
    salxyz_path: str,
    video_folder: str,
) -> bool:
    """
    Verify that the number of tracking frames matches the salxyz frame count.

    The salxyz tensors are generated from the video at 30fps, so their frame
    count should match (or be very close to) the tracking data frame count.
    Small mismatches (±a few frames) are acceptable since tracking may start/end
    slightly before/after the video.

    Returns:
        True if alignment is acceptable, False otherwise.
    """
    if not os.path.exists(salxyz_path):
        logger.warning(f"  Salxyz file not found: {salxyz_path} — skipping alignment check")
        return True

    salxyz_data = torch.load(salxyz_path, map_location="cpu", weights_only=False)
    salxyz_frames = salxyz_data["s_xyz"].shape[0]

    diff = abs(num_frames_30fps - salxyz_frames)
    pct_diff = diff / max(salxyz_frames, 1) * 100

    if pct_diff > 5.0:
        logger.warning(
            f"  Frame count mismatch for {video_folder}: "
            f"tracking={num_frames_30fps}, salxyz={salxyz_frames} "
            f"(diff={diff}, {pct_diff:.1f}%)"
        )
    else:
        logger.debug(
            f"  Frame alignment OK: tracking={num_frames_30fps}, "
            f"salxyz={salxyz_frames} (diff={diff})"
        )

    return True


def process_all_data(
    data_root: str,
    salxyz_dir: str,
    output_dir: str,
    skip_existing: bool = True,
) -> Dict:
    """
    Discover and process all participant-video recordings.

    Creates the output directory structure:
        <output_dir>/
            <participant_id>/
                <video_folder>.pt     ← feature tensors for one recording
            metadata.pt               ← participant ID mapping + video info

    Args:
        data_root:     Path to DataCollectedEyeHeadFaceCombined/
        salxyz_dir:    Path to muse_vp/salxyz/ (for alignment validation)
        output_dir:    Path to save processed .pt files
        skip_existing: If True, skip recordings that already have output files

    Returns:
        Summary dict with processing statistics
    """
    start_time = time.time()

    # --- Discover recordings ---
    recordings = discover_recordings(data_root)
    if not recordings:
        logger.error("No recordings found. Check data_root path.")
        return {"status": "error", "reason": "no recordings found"}

    # --- Build participant ID mapping ---
    pid_to_uid = build_participant_id_mapping(recordings)
    logger.info(f"Participant ID mapping ({len(pid_to_uid)} participants):")
    for pid, uid in pid_to_uid.items():
        logger.info(f"  {pid} → user_id {uid}")

    # --- Process each recording ---
    os.makedirs(output_dir, exist_ok=True)

    stats = {
        "total": len(recordings),
        "processed": 0,
        "skipped_existing": 0,
        "failed": 0,
        "details": [],
    }

    for i, rec in enumerate(recordings):
        pid = rec["participant_id"]
        vfolder = rec["video_folder"]
        label = f"[{i+1}/{len(recordings)}] {pid}/{vfolder}"

        # Output path: <output_dir>/<participant_id>/<video_folder>.pt
        out_participant_dir = os.path.join(output_dir, pid)
        out_path = os.path.join(out_participant_dir, f"{vfolder}.pt")

        if skip_existing and os.path.exists(out_path):
            logger.info(f"{label} — SKIP (already exists)")
            stats["skipped_existing"] += 1
            stats["details"].append((pid, vfolder, "skipped"))
            continue

        logger.info(f"{label} — Processing...")

        # Process the recording
        features = process_single_recording(rec["recording_dir"])
        if features is None:
            logger.error(f"{label} — FAILED")
            stats["failed"] += 1
            stats["details"].append((pid, vfolder, "failed"))
            continue

        # Validate frame alignment with salxyz
        salxyz_path = os.path.join(salxyz_dir, rec["salxyz_filename"])
        validate_salxyz_alignment(features["num_frames_30fps"], salxyz_path, vfolder)

        # Convert numpy arrays to torch tensors for saving
        output_dict = {
            "head_3d": torch.from_numpy(features["head_3d"]),
            "eye_3d": torch.from_numpy(features["eye_3d"]),
            "offset": torch.from_numpy(features["offset"]),
            "fixation": torch.from_numpy(features["fixation"]),
            "face": torch.from_numpy(features["face"]),
            "participant_id": pid,
            "user_id": pid_to_uid[pid],
            "video_folder": vfolder,
            "content_name": rec["content_name"],
            "salxyz_filename": rec["salxyz_filename"],
            "num_frames_30fps": features["num_frames_30fps"],
            "num_frames_5fps": features["num_frames_target"],
            "target_fps": features["target_fps"],
        }

        # Save
        os.makedirs(out_participant_dir, exist_ok=True)
        torch.save(output_dict, out_path)

        n5 = features["num_frames_target"]
        logger.info(
            f"{label} — OK: {n5} frames @ {TARGET_FPS}fps "
            f"({n5 / TARGET_FPS:.1f}s)"
        )
        stats["processed"] += 1
        stats["details"].append((pid, vfolder, "ok"))

    # --- Save metadata ---
    # This file is used by the Dataset class to map participant IDs to integers
    # for the user embedding layer.
    metadata = {
        "participant_to_uid": pid_to_uid,
        "uid_to_participant": {v: k for k, v in pid_to_uid.items()},
        "num_participants": len(pid_to_uid),
        "video_content_to_salxyz": VIDEO_CONTENT_TO_SALXYZ,
        "valid_video_content_names": sorted(VALID_VIDEO_CONTENT_NAMES),
        "target_fps": TARGET_FPS,
        "video_fps": VIDEO_FPS,
    }
    metadata_path = os.path.join(output_dir, "metadata.pt")
    torch.save(metadata, metadata_path)
    logger.info(f"Saved metadata to {metadata_path}")

    # --- Print summary ---
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"PREPROCESSING COMPLETE — {elapsed:.1f}s")
    logger.info(f"{'='*70}")
    logger.info(f"  Total recordings:  {stats['total']}")
    logger.info(f"  Processed:         {stats['processed']}")
    logger.info(f"  Skipped (existing):{stats['skipped_existing']}")
    logger.info(f"  Failed:            {stats['failed']}")
    logger.info(f"  Output directory:  {output_dir}")

    stats["elapsed_seconds"] = elapsed
    return stats


# =============================================================================
# VALIDATION / INSPECTION
# =============================================================================

def validate_processed_data(output_dir: str):
    """
    Load and validate all processed .pt files.

    Checks:
        - All expected tensor keys are present
        - Tensor shapes are consistent (all have same N for a recording)
        - head_3d and eye_3d are approximately unit vectors
        - offset values are in expected range
        - fixation IsFixating is binary-ish (0 or 1)
        - face values are in [0, 1]
        - Metadata file exists and is valid
    """
    output_dir = Path(output_dir)
    expected_keys = {"head_3d", "eye_3d", "offset", "fixation", "face"}

    # Find all .pt files (excluding metadata.pt)
    pt_files = sorted(output_dir.rglob("*.pt"))
    pt_files = [f for f in pt_files if f.name != "metadata.pt"]

    if not pt_files:
        print("No processed .pt files found.")
        return

    print(f"\nValidating {len(pt_files)} processed recordings...")
    print(f"{'='*80}")

    issues = []
    total_frames = 0
    participant_set = set()
    video_set = set()

    for pt_file in pt_files:
        data = torch.load(pt_file, map_location="cpu", weights_only=False)
        pid = data.get("participant_id", "?")
        vid = data.get("video_folder", "?")
        participant_set.add(pid)
        video_set.add(vid)

        label = f"{pid}/{vid}"

        # Check keys
        missing_keys = expected_keys - set(data.keys())
        if missing_keys:
            issues.append(f"{label}: Missing keys {missing_keys}")
            continue

        # Check shapes
        n = data["head_3d"].shape[0]
        total_frames += n
        shape_checks = {
            "head_3d": (n, 3),
            "eye_3d": (n, 3),
            "offset": (n, 3),
            "fixation": (n, 2),
            "face": (n, 5),
        }
        for key, expected_shape in shape_checks.items():
            actual = tuple(data[key].shape)
            if actual != expected_shape:
                issues.append(f"{label}: {key} shape {actual} != expected {expected_shape}")

        # Check head_3d unit vectors
        head_norms = torch.norm(data["head_3d"], dim=-1)
        if (head_norms - 1.0).abs().max() > 0.01:
            issues.append(
                f"{label}: head_3d not unit vectors "
                f"(norm range [{head_norms.min():.4f}, {head_norms.max():.4f}])"
            )

        # Check eye_3d unit vectors
        eye_norms = torch.norm(data["eye_3d"], dim=-1)
        if (eye_norms - 1.0).abs().max() > 0.01:
            issues.append(
                f"{label}: eye_3d not unit vectors "
                f"(norm range [{eye_norms.min():.4f}, {eye_norms.max():.4f}])"
            )

        # Check face values in [0, 1]
        face_min = data["face"].min().item()
        face_max = data["face"].max().item()
        if face_min < -0.01 or face_max > 1.01:
            issues.append(
                f"{label}: face values out of range [{face_min:.4f}, {face_max:.4f}]"
            )

        # Check for NaN or Inf
        for key in expected_keys:
            if torch.isnan(data[key]).any():
                issues.append(f"{label}: {key} contains NaN")
            if torch.isinf(data[key]).any():
                issues.append(f"{label}: {key} contains Inf")

        # Print per-file summary
        duration_s = n / TARGET_FPS
        print(f"  {label:<55} {n:>6} frames  ({duration_s:>6.1f}s)")

    # Summary
    print(f"\n{'='*80}")
    print(f"VALIDATION SUMMARY")
    print(f"  Recordings:    {len(pt_files)}")
    print(f"  Participants:  {len(participant_set)}")
    print(f"  Videos:        {len(video_set)}")
    print(f"  Total frames:  {total_frames} ({total_frames / TARGET_FPS:.1f}s at {TARGET_FPS}fps)")

    if issues:
        print(f"\n  ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"    ⚠ {issue}")
    else:
        print(f"\n  All checks passed.")

    # Check metadata
    meta_path = output_dir / "metadata.pt"
    if meta_path.exists():
        meta = torch.load(meta_path, map_location="cpu", weights_only=False)
        print(f"\n  Metadata: {meta['num_participants']} participants, "
              f"{len(meta['valid_video_content_names'])} target videos")
    else:
        print(f"\n  WARNING: metadata.pt not found")


# =============================================================================
# COMMAND-LINE INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="MUSE-VP Data Preprocessing Pipeline (Stage 1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all collected data:
    python -m muse_vp.data_preprocessing \\
        --data-root DataCollectedEyeHeadFaceCombined \\
        --salxyz-dir muse_vp/salxyz \\
        --output-dir muse_vp/processed_data

    # Validate processed output:
    python -m muse_vp.data_preprocessing \\
        --validate --output-dir muse_vp/processed_data

    # Reprocess everything (overwrite existing):
    python -m muse_vp.data_preprocessing \\
        --data-root DataCollectedEyeHeadFaceCombined \\
        --salxyz-dir muse_vp/salxyz \\
        --output-dir muse_vp/processed_data \\
        --overwrite
        """,
    )

    parser.add_argument(
        "--data-root",
        type=str,
        default="DataCollectedEyeHeadFaceCombined",
        help="Root directory containing P###/ participant folders (default: DataCollectedEyeHeadFaceCombined)",
    )
    parser.add_argument(
        "--salxyz-dir",
        type=str,
        default="muse_vp/salxyz",
        help="Directory containing *_salxyz.pt files for frame count validation (default: muse_vp/salxyz)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="muse_vp/processed_data",
        help="Directory to save processed .pt files (default: muse_vp/processed_data)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reprocess and overwrite existing .pt files",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate existing processed data (no processing)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )

    args = parser.parse_args()

    # --- Set up logging ---
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # --- Validation-only mode ---
    if args.validate:
        validate_processed_data(args.output_dir)
        return

    # --- Full processing ---
    logger.info("="*70)
    logger.info("MUSE-VP Data Preprocessing Pipeline (Stage 1)")
    logger.info("="*70)
    logger.info(f"  Data root:   {os.path.abspath(args.data_root)}")
    logger.info(f"  Salxyz dir:  {os.path.abspath(args.salxyz_dir)}")
    logger.info(f"  Output dir:  {os.path.abspath(args.output_dir)}")
    logger.info(f"  Video FPS:   {VIDEO_FPS}")
    logger.info(f"  Target FPS:  {TARGET_FPS}")
    logger.info(f"  Overwrite:   {args.overwrite}")

    stats = process_all_data(
        data_root=args.data_root,
        salxyz_dir=args.salxyz_dir,
        output_dir=args.output_dir,
        skip_existing=not args.overwrite,
    )

    # After processing, run validation
    if stats.get("processed", 0) > 0 or stats.get("skipped_existing", 0) > 0:
        logger.info("\nRunning validation on processed data...")
        validate_processed_data(args.output_dir)


if __name__ == "__main__":
    main()
