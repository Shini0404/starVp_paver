# MUSE-VP: FINAL ARCHITECTURE — The Complete Blueprint

## Multi-Modal User-Specific Enhanced Viewport Prediction in 360° Videos

---

# OVERVIEW: What Are We Building?

We are building a system that answers this question:

> **"User #7 is watching a 360° basketball video. Their head is pointing at the court center, but their eyes are drifting toward the right where a player just received the ball, and their face shows surprise. Where will their head be in 1-5 seconds?"**

The system takes 5 types of input and produces 1 output:

```
INPUTS:                                          OUTPUT:
① 360° Video frames          ─┐
② Past head positions         │
③ Past eye gaze positions     ├──→  [MUSE-VP]  ──→  Future head positions
④ Past face expressions       │                      (next 1-5 seconds)
⑤ User identity (who)        ─┘
```

---

# THE FULL PIPELINE: 8 STAGES

Here is EVERY stage, from raw data to final prediction.
I'll explain each one in extreme detail below.

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        MUSE-VP COMPLETE PIPELINE                             ║
║                                                                              ║
║  ┌─────────────┐                                                             ║
║  │  STAGE 0    │  Raw Data Collection                                        ║
║  │  (OFFLINE)  │  Video files + CSV tracking files + User IDs                ║
║  └──────┬──────┘                                                             ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌─────────────┐                                                             ║
║  │  STAGE 1    │  Data Preprocessing                                         ║
║  │  (OFFLINE)  │  CSV → aligned, normalized feature tensors                  ║
║  └──────┬──────┘                                                             ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌─────────────┐                                                             ║
║  │  STAGE 2    │  PAVER Saliency Generation  ❄️ FROZEN                       ║
║  │  (OFFLINE)  │  Video → 2D saliency heatmaps                              ║
║  └──────┬──────┘                                                             ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌─────────────┐                                                             ║
║  │  STAGE 3    │  SalMap Processor  ❄️ FROZEN                                ║
║  │  (OFFLINE)  │  2D saliency → 3D sphere points + weights                  ║
║  └──────┬──────┘                                                             ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌─────────────┐                                                             ║
║  │  STAGE 4    │  Dataset & DataLoader Creation                              ║
║  │  (OFFLINE)  │  Create sliding windows, splits, batching                   ║
║  └──────┬──────┘                                                             ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌──────────────────────────────────────────────────────────────────┐        ║
║  │  STAGE 5    │  🧠 MUSE-VP MODEL (THE CORE — TRAINED)           │        ║
║  │             │                                                    │        ║
║  │   5A: Dual-Stream LSTM  (head stream + eye stream)              │        ║
║  │   5B: Eye-Guided Spatial Attention Module                       │        ║
║  │   5C: Temporal Attention Module (unchanged from STAR-VP)        │        ║
║  │   5D: Face-Modulated Gating Fusion                              │        ║
║  │   5E: User Personalization Embedding                            │        ║
║  │                                                                  │        ║
║  └──────┬──────────────────────────────────────────────────────────┘        ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌─────────────┐                                                             ║
║  │  STAGE 6    │  Loss Computation & Training                                ║
║  │             │  Geodesic loss on predicted vs actual head positions         ║
║  └──────┬──────┘                                                             ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌─────────────┐                                                             ║
║  │  STAGE 7    │  Evaluation & Ablation                                      ║
║  │             │  Geodesic error, overlap ratio, per-horizon error            ║
║  └─────────────┘                                                             ║
║                                                                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

# STAGE 0: RAW DATA (What We Already Have)

## What exists right now:

| Data | Location | Format |
|------|----------|--------|
| 18 × 360° videos | `PAVER/data/wu_mmsys_17/` | `.mp4` files |
| PAVER saliency maps (all 18 videos) | `PAVER/code/qual/*_saliency.pt` | PyTorch tensors `[frames, 224, 448]` |
| SalMap Processor output (all 18 videos) | `muse_vp/salxyz/*_salxyz.pt` | `{s_xyz: [frames, 32, 3], s_weight: [frames, 32]}` |
| Wu_MMSys_17 head tracking (48 users) | `vr-dataset/Formated_Data/` | CSV files (head orientation only) |
| YOUR collected data (per participant) | Your CSV files | `head.csv`, `eye.csv`, `face.csv`, `combined.csv` |

## What we still need to collect:
- Eye + Face + Head tracking from 25+ participants watching 14 selected videos on Meta Quest Pro

---

# STAGE 1: DATA PREPROCESSING

## What happens here:

Raw CSVs (messy, different sample rates, different units) → Clean, aligned, normalized tensors ready for the model.

### Input:
```
Per participant per video:
  head.csv     → HeadTimestamp, EulerYaw, EulerPitch, EulerRoll, ...
  eye.csv      → EyeTimestamp, GazeYaw, GazePitch, IsFixating, FixationDurationMs, ...
  face.csv     → FaceTimestamp, Brow_Lowerer_L, Jaw_Drop, Eyes_Closed_L, ...
  combined.csv → Timestamp, GazeRelativeH, GazeRelativeV, EyeHeadOffset, FaceActivity, ...
```

### Processing Steps:

**Step 1.1: Temporal Alignment (resample to video fps)**
```
Video fps = 30fps (typically for Wu_MMSys_17)
Tracking data = ~72Hz

For each video frame time t_frame (at 1/30 sec intervals):
  → Find closest tracking sample OR linearly interpolate
  → Result: one tracking sample per video frame
```

**Step 1.2: Convert angles to 3D unit vectors**
```
For head: (EulerYaw, EulerPitch) → (hx, hy, hz) unit vector

  hx = cos(pitch_rad) × sin(yaw_rad)
  hy = sin(pitch_rad)
  hz = cos(pitch_rad) × cos(yaw_rad)

Same for eye: (GazeYaw, GazePitch) → (ex, ey, ez) unit vector
```

**Step 1.3: Normalize features to similar ranges**
```
Head 3D:       already unit vectors → range [-1, 1]            ← NO CHANGE
Eye 3D:        already unit vectors → range [-1, 1]            ← NO CHANGE
GazeRelativeH: degrees → divide by 30°  → range ~[-1, 1]      ← NORMALIZE
GazeRelativeV: degrees → divide by 30°  → range ~[-1, 1]      ← NORMALIZE
EyeHeadOffset: degrees → divide by 30°  → range ~[0, 1]       ← NORMALIZE
IsFixating:    already 0 or 1           → range [0, 1]         ← NO CHANGE
FixationDurMs: milliseconds → divide by 1000, cap at 1.0       ← NORMALIZE
FaceActivity:  already ~[0, 1]          → range [0, 1]         ← NO CHANGE
Brow/Jaw/Eyes: already ~[0, 1]          → range [0, 1]         ← NO CHANGE
```

**Step 1.4: Downsample (optional)**
```
STAR-VP uses 5fps (downsampled from 30fps)
This means 1 sample every 6 frames

5 seconds of past data at 5fps = 25 timesteps (T_M = 25)
5 seconds of future prediction at 5fps = 25 timesteps (T_H = 25)

Alternatively: keep at 30fps but use shorter windows
  → We'll experiment with both
```

### Output of Stage 1:

Per participant per video, we get aligned tensors:

```
head_3d:       [num_frames, 3]     ← 3D head direction (unit vector)
eye_3d:        [num_frames, 3]     ← 3D eye gaze direction (unit vector)
offset:        [num_frames, 3]     ← (relH/30, relV/30, magnitude/30)
fixation:      [num_frames, 2]     ← (IsFixating, FixDuration_normalized)
face:          [num_frames, 5]     ← (FaceActivity, BrowLower, JawDrop, EyesClosed, BrowRaise)
user_id:       scalar integer      ← which participant (0 to N-1)
```

Total feature dimensions per frame:

| Feature Group | Dimensions | Used In |
|--------------|------------|---------|
| head_3d | 3 | LSTM (head stream) + Spatial Attention |
| eye_3d | 3 | LSTM (eye stream) + Spatial Attention |
| offset | 3 | LSTM (eye stream) |
| fixation | 2 | LSTM (eye stream) |
| face | 5 | Gating Fusion |
| user_id | 1 (integer) | User Embedding |
| **Total** | **17 + 1 ID** | |

---

# STAGE 2: PAVER SALIENCY GENERATION ❄️

**Already done. No changes.**

### Input:
```
360° video file (.mp4)
  Example: exp2_video_04_Female_Basketball_Match.mp4
```

### What happens:
```
Video frames → [PAVER ViT] → saliency score per pixel per frame
```

### Output:
```
*_saliency.pt: tensor of shape [num_frames, 224, 448]
  Each value ∈ [0, 1] = "how interesting is this pixel"
  
Example: exp2_video_04 has 10,829 frames
  → Output: [10829, 224, 448] float32 tensor
```

### Status: ✅ DONE for all 18 videos

---

# STAGE 3: SALMAP PROCESSOR ❄️

**Already done. No changes.**

### Input:
```
*_saliency.pt: [num_frames, 224, 448] saliency heatmaps
```

### What happens:
```
For each frame:
  1. Map every pixel (row, col) → 3D point (x, y, z) on unit sphere
  2. Multiply saliency value by cos(latitude) to correct for equirectangular distortion
  3. Pick the top-K (K=32) most salient pixels
  4. Look up their 3D sphere coordinates
  5. Normalize their weights to sum to 1.0
```

### Output:
```
*_salxyz.pt: dictionary with:
  s_xyz:    [num_frames, 32, 3]   ← 3D locations of top-32 salient points
  s_weight: [num_frames, 32]      ← importance weights (sum to 1.0 per frame)
```

### Status: ✅ DONE for all 18 videos

---

# STAGE 4: DATASET & DATALOADER CREATION

This stage turns everything into sliding windows for training.

### Input:
```
Per participant per video:
  head_3d:     [num_frames, 3]
  eye_3d:      [num_frames, 3]
  offset:      [num_frames, 3]
  fixation:    [num_frames, 2]
  face:        [num_frames, 5]
  user_id:     integer

Per video:
  s_xyz:       [num_frames, 32, 3]
  s_weight:    [num_frames, 32]
```

### What happens:

**Sliding window creation:**
```
Parameters:
  T_M = 25  (past window: 5 seconds at 5fps)
  T_H = 25  (future window: 5 seconds at 5fps)
  stride = 5 (slide window by 1 second = 5 frames at 5fps)

For each valid starting position t:
  Past window:   frames [t, t+1, ..., t+T_M-1]          (what the model SEES)
  Future window:  frames [t+T_M, t+T_M+1, ..., t+T_M+T_H-1]  (what the model PREDICTS)
```

**Example** with a 60-second video at 5fps = 300 frames:
```
Window 1:  past=[0..24],   future=[25..49]    → predict seconds 5-10
Window 2:  past=[5..29],   future=[30..54]    → predict seconds 6-11
Window 3:  past=[10..34],  future=[35..59]    → predict seconds 7-12
...
Window 52: past=[255..279], future=[280..299] → last valid window
```

### One training sample looks like:

```python
sample = {
    # ===== LSTM INPUTS (past T_M timesteps) =====
    'head_3d':     [T_M, 3],        # past head trajectory (3D unit vectors)
    'eye_3d':      [T_M, 3],        # past eye gaze trajectory (3D unit vectors)
    'offset':      [T_M, 3],        # past eye-head offset (normalized)
    'fixation':    [T_M, 2],        # past fixation state
    
    # ===== SPATIAL ATTENTION INPUTS (future T_H timesteps) =====
    's_xyz':       [T_H, 32, 3],    # salient 3D points for FUTURE frames
    's_weight':    [T_H, 32],       # salient point weights for FUTURE frames
    
    # ===== GATING INPUTS (current moment) =====
    'face':        [5],             # face features (averaged over last few past frames)
    
    # ===== PERSONALIZATION =====
    'user_id':     scalar int,       # participant ID
    
    # ===== GROUND TRUTH (what we predict) =====
    'target_head': [T_H, 3],        # actual future head trajectory (3D unit vectors)
}
```

### Output of Stage 4:

```
train_dataset:  ~70% of all windows (from train videos/users)
val_dataset:    ~15% of all windows
test_dataset:   ~15% of all windows

Each dataset returns batches of the sample structure above.
Batch size = 32
```

---

# STAGE 5: 🧠 THE MUSE-VP MODEL (The Core)

This is where all the magic happens. 5 sub-modules.

## THE BIG PICTURE DIAGRAM

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                 ║
║                         STAGE 5: MUSE-VP MODEL                                  ║
║                                                                                 ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │  5E: USER PERSONALIZATION                                                │   ║
║  │                                                                          │   ║
║  │  user_id (int) → [Embedding Table] → u_k (R^32)                        │   ║
║  │                                        │                                 │   ║
║  │                               ┌────────┴────────┐                       │   ║
║  │                               ▼                  ▼                       │   ║
║  │                    h_0 = tanh(W_h·u_k)    c_0 = tanh(W_c·u_k)          │   ║
║  │                               │                  │                       │   ║
║  └───────────────────────────────┼──────────────────┼───────────────────────┘   ║
║                                  │                  │                            ║
║                                  ▼                  ▼                            ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │  5A: DUAL-STREAM LSTM MODULE                                             │   ║
║  │                                                                          │   ║
║  │  HEAD STREAM:                                                            │   ║
║  │  head_3d [T_M,3] ────→ [LSTM_head] ─────→ h_head [hidden_dim]          │   ║
║  │                          h_0, c_0 from user embedding                    │   ║
║  │                                                                          │   ║
║  │  EYE STREAM:                                                             │   ║
║  │  eye_3d [T_M,3] ──┐                                                     │   ║
║  │  offset [T_M,3] ──┼→ Concat → [T_M,8] → [LSTM_eye] → h_eye [hidden]   │   ║
║  │  fixation [T_M,2]─┘                       h_0=0, c_0=0                  │   ║
║  │                                                                          │   ║
║  │  FUSION:                                                                 │   ║
║  │  h_combined = Concat(h_head, h_eye) → [Linear] → P'  [T_H, 3]         │   ║
║  │                                                    │                     │   ║
║  │  Also output: P_{s-in} (viewpoint features for spatial attention)       │   ║
║  │               = P' reshaped for attention                                │   ║
║  └──────────────────────────────────────────────────┼───────────────────────┘   ║
║                                                     │                            ║
║                                      ┌──────────────┤                            ║
║                                      │              │                            ║
║                                      ▼              ▼                            ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │  5B: EYE-GUIDED SPATIAL ATTENTION MODULE                                 │   ║
║  │                                                                          │   ║
║  │  INPUTS:                                                                 │   ║
║  │    P_{s-in}   [T_H, d_P]  ← viewpoint features (from LSTM)             │   ║
║  │    S_{s-in}   [T_H, K, d_S] ← saliency features (from SalMap Proc)     │   ║
║  │    E_gaze_3d  [T_H, 3]    ← eye gaze direction (3D vector) ⭐ NEW      │   ║
║  │                                                                          │   ║
║  │  ENRICHMENT:                                                             │   ║
║  │    P̂_{s-in} = Concat(P_{s-in}, E_gaze_3d) → [T_H, d_P + 3]  ⭐ NEW   │   ║
║  │                                                                          │   ║
║  │  ENCODER (viewpoint attends to saliency):                                │   ║
║  │    Q = Linear_Q(P̂_{s-in})                                              │   ║
║  │    K = Linear_K(S_{s-in})                                                │   ║
║  │    V = Linear_V(S_{s-in})                                                │   ║
║  │    S_{s-out} = LayerNorm(softmax(QK^T/√d)·V + S_{s-in})                │   ║
║  │                                                                          │   ║
║  │  DECODER (saliency attends to viewpoint):                                │   ║
║  │    Q = Linear_Q(S_{s-in})                                                │   ║
║  │    K = Linear_K(P̂_{s-in})                                              │   ║
║  │    V = Linear_V(P̂_{s-in})                                              │   ║
║  │    P_{s-out} = LayerNorm(softmax(QK^T/√d)·V + P_{s-in})                │   ║
║  │                                                                          │   ║
║  │  OUTPUT:                                                                 │   ║
║  │    S_{s-out}  [T_H, K, d_S]   ← refined saliency features              │   ║
║  │    P_{s-out}  [T_H, d_P]      ← refined viewpoint features              │   ║
║  └──────────────────────────────────────────────────────────────────────────┘   ║
║                                      │                                           ║
║                                      ▼                                           ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │  5C: TEMPORAL ATTENTION MODULE (UNCHANGED FROM STAR-VP)                  │   ║
║  │                                                                          │   ║
║  │  INPUT:                                                                  │   ║
║  │    C_t = Concat_temporal(P', S_{s-out}, P_{s-out}, PositionalEmb)       │   ║
║  │                                                                          │   ║
║  │  ENCODER: Self-attention across concatenated temporal sequence            │   ║
║  │  DECODER: Cross-attention to produce future predictions                  │   ║
║  │                                                                          │   ║
║  │  OUTPUT:                                                                 │   ║
║  │    P''  [T_H, 3]  ← content-aware temporal prediction                  │   ║
║  └──────────────────────────────────────────────────────────────────────────┘   ║
║                                      │                                           ║
║                                      ▼                                           ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │  5D: FACE-MODULATED GATING FUSION  ⭐ MODIFIED                          │   ║
║  │                                                                          │   ║
║  │  INPUTS:                                                                 │   ║
║  │    P'     [T_H, 3]   ← trajectory-only prediction (from LSTM)          │   ║
║  │    P''    [T_H, 3]   ← content-aware prediction (from Temporal Attn)    │   ║
║  │    F_face [d_f]      ← face engagement embedding  ⭐ NEW               │   ║
║  │                                                                          │   ║
║  │  FUSION:                                                                 │   ║
║  │    C_f = Concat(Flatten(P'), Flatten(P''), F_face)                      │   ║
║  │    G   = σ(W_2 · ReLU(W_1 · C_f + b_1) + b_2)                         │   ║
║  │    W'  = G[:T_H×3]     ← weight for trajectory prediction              │   ║
║  │    W'' = G[T_H×3:]     ← weight for content prediction                 │   ║
║  │    P̂  = W' ⊗ P' + W'' ⊗ P''                                          │   ║
║  │                                                                          │   ║
║  │  OUTPUT:                                                                 │   ║
║  │    P̂  [T_H, 3]  ← FINAL predicted future head positions               │   ║
║  └──────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                 ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

# STAGE 5A: DUAL-STREAM LSTM MODULE (Detailed)

## Why Dual-Stream Instead of Single LSTM?

In the previous ARCHITECTURE_PROPOSAL.md, I proposed a single LSTM with 11D input.
After analyzing the MFTR paper (which uses separate LSTMs for head and eye), 
I now recommend **dual-stream** because:

1. **Head and eye move at DIFFERENT speeds** — head is slow (~100°/s max), eyes are fast (~500°/s)
2. **Different temporal patterns** — head movements are smooth, eye movements are jerky (saccades)
3. **Separate LSTMs can specialize** — one learns head momentum, the other learns gaze patterns
4. **MFTR proves this works** — they already showed separate encoding helps

However, we keep the single-LSTM as an ablation experiment for comparison.

## Architecture Detail

```
                    ┌───────────────────────────────────────────┐
                    │         5A: DUAL-STREAM LSTM              │
                    │                                           │
   head_3d          │  ┌─────────────────────────────────┐     │
   [T_M, 3]   ────►│  │  LSTM_head                      │     │
                    │  │  input_dim = 3                   │     │
                    │  │  hidden_dim = 128                │     │
                    │  │  num_layers = 1                  │     │
                    │  │  h_0 = tanh(W_h · u_k + b_h)    │     │
                    │  │  c_0 = tanh(W_c · u_k + b_c)    │     │    Concat
                    │  │         │                        │     │     ┌──┐
                    │  │         ▼                        │     │     │  │
                    │  │  h_head = last hidden [128]      │─────┼────►│  │──► [Linear] ──► P'
                    │  └─────────────────────────────────┘     │     │  │     [256→T_H×3]   [T_H, 3]
                    │                                           │     │  │
   eye_3d           │  ┌─────────────────────────────────┐     │     │  │
   [T_M, 3]   ──┐  │  │  LSTM_eye                       │     │     │  │
   offset    ────┼──│  │  input_dim = 8                  │     │     │  │
   [T_M, 3]     │  │  │  hidden_dim = 128                │     │     │  │
   fixation  ────┘  │  │  num_layers = 1                 │     │     └──┘
   [T_M, 2] Concat  │  │  h_0 = 0 (zero init)           │     │
             =[T_M,8]  │  c_0 = 0                        │     │
                    │  │         │                        │     │
                    │  │         ▼                        │     │
                    │  │  h_eye = last hidden [128]       │─────┘
                    │  └─────────────────────────────────┘     │
                    │                                           │
                    └───────────────────────────────────────────┘
```

## Equations for Stage 5A

### User Embedding → LSTM Initialization (for head LSTM only)

```
u_k = EmbeddingTable[user_id]                    u_k ∈ R^{d_u},  d_u = 32

h_0^{head} = tanh(W_h · u_k + b_h)              h_0 ∈ R^{128}
c_0^{head} = tanh(W_c · u_k + b_c)              c_0 ∈ R^{128}

h_0^{eye} = 0                                    (zero vector)
c_0^{eye} = 0
```

**Why only initialize head LSTM with user embedding?**
Because the user's "personality" (explorer vs focused vs passive) primarily affects HEAD movement patterns. Eye movements are more reflexive and less user-specific.

### Head LSTM Forward Pass

```
For i = 1 to T_M:
    h_i^{head}, c_i^{head} = LSTM_head(head_3d_i, h_{i-1}^{head}, c_{i-1}^{head})

h_head = h_{T_M}^{head} ∈ R^{128}
```

### Eye LSTM Forward Pass

```
For i = 1 to T_M:
    eye_input_i = Concat(eye_3d_i, offset_i, fixation_i) ∈ R^{8}
    h_i^{eye}, c_i^{eye} = LSTM_eye(eye_input_i, h_{i-1}^{eye}, c_{i-1}^{eye})

h_eye = h_{T_M}^{eye} ∈ R^{128}
```

### Combining Both Streams

```
h_combined = Concat(h_head, h_eye) ∈ R^{256}

P' = Reshape(Linear_out(h_combined)) ∈ R^{T_H × 3}

where Linear_out: R^{256} → R^{T_H × 3}
```

### Inputs & Outputs Summary

| | Shape | Description |
|--|-------|-------------|
| **Input: head_3d** | `[batch, T_M, 3]` | Past head positions as 3D unit vectors |
| **Input: eye_3d** | `[batch, T_M, 3]` | Past eye gaze as 3D unit vectors |
| **Input: offset** | `[batch, T_M, 3]` | Normalized eye-head offset (relH, relV, mag) |
| **Input: fixation** | `[batch, T_M, 2]` | IsFixating + FixationDuration |
| **Input: user_id** | `[batch]` | Integer user IDs |
| **Output: P'** | `[batch, T_H, 3]` | Initial predicted future head positions |

### Intuition (Easy Language)

Think of two people watching a security camera feed together:
- **Person 1 (head LSTM)**: Only watches where the security camera is pointing. "Camera has been panning left for 3 seconds, it'll probably keep going left."
- **Person 2 (eye LSTM)**: Watches where the guard's EYES are looking. "Guard's eyes just darted right — he spotted something! The camera will swing right soon."

**Together (concat)**: "Camera is panning left, BUT guard's eyes are going right → camera will STOP panning left and swing right." This prediction is better than either person alone.

---

# STAGE 5B: EYE-GUIDED SPATIAL ATTENTION MODULE (Detailed)

## What this module does (simple)

This module answers: **"Given where the user is heading AND where their eyes are looking, which salient regions in the video are most relevant?"**

It's like a spotlight: the head provides a general direction, the eyes NARROW the spotlight to the exact region of interest.

## Architecture Detail

```
┌────────────────────────────────────────────────────────────────────────────┐
│                 5B: EYE-GUIDED SPATIAL ATTENTION                           │
│                                                                            │
│  INPUTS:                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                          │
│  │ P' (LSTM)  │  │  S_xyz     │  │ E_gaze_3d  │                          │
│  │ [T_H, 3]   │  │ [T_H,32,3] │  │ [T_H, 3]   │                          │
│  └─────┬──────┘  │ S_weight   │  └──────┬─────┘                          │
│        │         │ [T_H, 32]  │         │                                  │
│        │         └──────┬─────┘         │                                  │
│        │                │               │                                  │
│        │ ┌──────────────┘               │                                  │
│        │ │                              │                                  │
│        │ │    ┌─────────────────────────┘                                  │
│        │ │    │                                                            │
│        ▼ ▼    ▼                                                            │
│  ┌──────────────────────────────────────────────────┐                     │
│  │  PREPARE INPUTS                                   │                     │
│  │                                                   │                     │
│  │  Viewpoint tokens:                                │                     │
│  │    P_{s-in} = Linear_P(P') → [T_H, d_model]     │                     │
│  │                                                   │                     │
│  │  Eye gaze enrichment:  ⭐ NEW                     │                     │
│  │    E_proj = Linear_E(E_gaze_3d) → [T_H, d_eye]  │                     │
│  │    P̂_{s-in} = P_{s-in} + E_proj                 │                     │
│  │                   (additive enrichment)            │                     │
│  │                                                   │                     │
│  │  Saliency tokens:                                 │                     │
│  │    For each timestep t, for each of K=32 points:  │                     │
│  │    S_{s-in}[t,k] = Concat(S_xyz[t,k], S_weight[t,k]) → [T_H,32,4]   │
│  │    S_{s-in} = Linear_S(S_{s-in}) → [T_H, 32, d_model]               │
│  │                                                   │                     │
│  └───────────────────────┬───────────────────────────┘                     │
│                          │                                                  │
│                          ▼                                                  │
│  ┌──────────────────────────────────────────────────┐                     │
│  │  ENCODER (Viewpoint → Saliency attention)         │                     │
│  │                                                   │                     │
│  │  For each future timestep t:                      │                     │
│  │    Q = W_Q · P̂_{s-in}[t]       [1, d_model]     │                     │
│  │    K = W_K · S_{s-in}[t]        [32, d_model]    │                     │
│  │    V = W_V · S_{s-in}[t]        [32, d_model]    │                     │
│  │                                                   │                     │
│  │    Attention = softmax(Q·K^T / √d_model) · V     │                     │
│  │                                                   │                     │
│  │    S_{s-mid} = LayerNorm(Attention + S_{s-in})    │                     │
│  │    S_{s-out} = LayerNorm(MLP(S_{s-mid}) + S_{s-mid})                  │
│  └───────────────────────┬───────────────────────────┘                     │
│                          │                                                  │
│                          ▼                                                  │
│  ┌──────────────────────────────────────────────────┐                     │
│  │  DECODER (Saliency → Viewpoint attention)         │                     │
│  │                                                   │                     │
│  │  For each future timestep t:                      │                     │
│  │    Q = W_Q' · S_{s-in}[t]       [32, d_model]   │                     │
│  │    K = W_K' · P̂_{s-in}[t]      [1, d_model]     │                     │
│  │    V = W_V' · P̂_{s-in}[t]      [1, d_model]     │                     │
│  │                                                   │                     │
│  │    Attention = softmax(Q·K^T / √d_model) · V     │                     │
│  │                                                   │                     │
│  │    P_{s-mid} = LayerNorm(Attention + P_{s-in})    │                     │
│  │    P_{s-out} = LayerNorm(MLP(P_{s-mid}) + P_{s-mid})                  │
│  └───────────────────────┬───────────────────────────┘                     │
│                          │                                                  │
│  OUTPUT:                 │                                                  │
│    S_{s-out} [T_H, 32, d_model]  (refined saliency)                       │
│    P_{s-out} [T_H, d_model]      (refined viewpoint)                       │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## Equations for Stage 5B

### Input Preparation

```
P_{s-in} = Linear_P(P')                           ∈ R^{T_H × d_model}
E_proj   = Linear_E(E_gaze_3d)                    ∈ R^{T_H × d_model}
P̂_{s-in} = P_{s-in} + E_proj                      ∈ R^{T_H × d_model}   ⭐ EYE ENRICHMENT

S_input  = Concat(S_xyz, S_weight.unsqueeze(-1))   ∈ R^{T_H × K × 4}
S_{s-in} = Linear_S(S_input)                       ∈ R^{T_H × K × d_model}
```

Note: I switched from concatenation (`Concat(P_{s-in}, E_gaze_3d)`) to **additive enrichment** (`P_{s-in} + E_proj`). This is cleaner because:
- It keeps the dimension the same (no need to resize downstream layers)
- Addition means "shift the query toward where the eyes are looking"
- The linear projection learns what ASPECT of eye gaze is useful

### Encoder (Multi-Head Cross-Attention)

```
For each timestep t in [1, T_H]:

  Q_enc = W_Q · P̂_{s-in}[t]                       ∈ R^{1 × d_model}
  K_enc = W_K · S_{s-in}[t]                        ∈ R^{K × d_model}
  V_enc = W_V · S_{s-in}[t]                        ∈ R^{K × d_model}

  A_enc = softmax(Q_enc · K_enc^T / √d_k) · V_enc  ∈ R^{1 × d_model}

  With multi-head (h=4 heads):
    head_i = Attention(Q·W_Q^i, K·W_K^i, V·W_V^i)
    MultiHead = Concat(head_1, ..., head_h) · W_O

  S_{s-out}[t] = LayerNorm(MultiHead + S_{s-in}[t])
  S_{s-out}[t] = LayerNorm(MLP(S_{s-out}[t]) + S_{s-out}[t])
```

### Decoder (Multi-Head Cross-Attention, reversed)

```
For each timestep t in [1, T_H]:

  Q_dec = W_Q' · S_{s-in}[t]                       ∈ R^{K × d_model}
  K_dec = W_K' · P̂_{s-in}[t]                      ∈ R^{1 × d_model}
  V_dec = W_V' · P̂_{s-in}[t]                      ∈ R^{1 × d_model}

  A_dec = softmax(Q_dec · K_dec^T / √d_k) · V_dec  ∈ R^{K × d_model}

  P_{s-out}[t] = LayerNorm(A_dec + P_{s-in}[t])
  P_{s-out}[t] = LayerNorm(MLP(P_{s-out}[t]) + P_{s-out}[t])
```

### Inputs & Outputs Summary

| | Shape | Description |
|--|-------|-------------|
| **Input: P'** | `[batch, T_H, 3]` | LSTM predictions (from 5A) |
| **Input: S_xyz** | `[batch, T_H, 32, 3]` | 3D salient points (from SalMap Proc) |
| **Input: S_weight** | `[batch, T_H, 32]` | Saliency weights |
| **Input: E_gaze_3d** | `[batch, T_H, 3]` | Eye gaze direction (3D) ⭐ NEW |
| **Output: S_{s-out}** | `[batch, T_H, 32, d_model]` | Refined saliency features |
| **Output: P_{s-out}** | `[batch, T_H, d_model]` | Refined viewpoint features |

### Intuition (Easy Language)

**Without eye gaze (STAR-VP):**
Imagine you're in a dark room with a flashlight (your head). You shine the flashlight broadly — it highlights a general area. Now the model tries to figure out which highlighted things you care about. But the flashlight covers 100° — lots of things!

**With eye gaze (MUSE-VP):**
Now you have the flashlight (head) AND a laser pointer (eyes). The laser pointer pinpoints EXACTLY which thing in the flashlit area you're focused on. The model uses this precise pointer to pick the RIGHT salient features to pay attention to.

The `+ E_proj` in the equation is literally "shift the flashlight beam toward where the laser pointer is pointing."

---

# STAGE 5C: TEMPORAL ATTENTION MODULE (Unchanged)

## What it does (simple)

This module answers: **"How does the relationship between viewport and saliency CHANGE over time?"**

The spatial module (5B) works per-frame. This module looks ACROSS frames to see temporal trends.

## Architecture (Same as STAR-VP)

```
┌────────────────────────────────────────────────────────────────┐
│              5C: TEMPORAL ATTENTION (NO CHANGES)                │
│                                                                │
│  INPUTS:                                                       │
│    P'       [T_H, 3]           ← LSTM prediction              │
│    S_{s-out} [T_H, 32, d_model] ← spatial-refined saliency     │
│    P_{s-out} [T_H, d_model]    ← spatial-refined viewpoint     │
│    E_pos    [T_H, d_model]     ← learnable positional encoding │
│                                                                │
│  CONCATENATION along temporal dimension:                       │
│    C_t = Stack(P', S_{s-out}, P_{s-out}) + E_pos              │
│    (concatenates all temporal tokens into one long sequence)    │
│                                                                │
│  ENCODER: Self-attention over entire temporal sequence          │
│    → learns which time steps are related                       │
│                                                                │
│  DECODER: Cross-attention to produce output                    │
│    → generates refined predictions                             │
│                                                                │
│  OUTPUT:                                                       │
│    P'' [T_H, 3]  ← temporally refined predictions              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Inputs & Outputs Summary

| | Shape | Description |
|--|-------|-------------|
| **Input: P'** | `[batch, T_H, 3]` | From LSTM |
| **Input: S_{s-out}** | `[batch, T_H, 32, d_model]` | From Spatial Attention |
| **Input: P_{s-out}** | `[batch, T_H, d_model]` | From Spatial Attention |
| **Output: P''** | `[batch, T_H, 3]` | Content+time aware prediction |

### Intuition

Spatial attention knows: "At time t=3, there's a ball on the right."
Temporal attention adds: "The ball has been moving right since t=1 — by t=5 it'll be at the far right, and the user will follow."

---

# STAGE 5D: FACE-MODULATED GATING FUSION (Detailed)

## What it does (simple)

We now have TWO predictions:
- **P'** (from LSTM): "Based on head+eye movement patterns, the user will look HERE"
- **P''** (from attention): "Based on what's interesting in the video + movement, the user will look HERE"

Sometimes these agree. Sometimes they don't. This module DECIDES which to trust.

**Face expressions help this decision.** If the user looks surprised (something unexpected happened), trust the content prediction. If the user is passive, trust the trajectory prediction.

## Architecture Detail

```
┌─────────────────────────────────────────────────────────────────────────┐
│              5D: FACE-MODULATED GATING FUSION                           │
│                                                                         │
│  INPUTS:                                                                │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐                       │
│  │ P'       │   │ P''      │   │ face_raw     │                       │
│  │[T_H, 3]  │   │[T_H, 3]  │   │[5]           │                       │
│  └────┬─────┘   └────┬─────┘   └──────┬───────┘                       │
│       │              │                  │                               │
│       │              │                  ▼                               │
│       │              │          ┌──────────────┐                       │
│       │              │          │ Linear_face  │                       │
│       │              │          │ 5 → 16       │                       │
│       │              │          │ + ReLU       │                       │
│       │              │          └──────┬───────┘                       │
│       │              │                 │                                │
│       │              │                 ▼                                │
│       │              │          F_face [16]  (face embedding)          │
│       │              │                 │                                │
│       ▼              ▼                 ▼                                │
│  ┌──────────────────────────────────────────┐                          │
│  │  Flatten + Concatenate                    │                          │
│  │                                           │                          │
│  │  flat_P'  = Flatten(P')  → [T_H × 3]    │                          │
│  │  flat_P'' = Flatten(P'') → [T_H × 3]    │                          │
│  │                                           │                          │
│  │  C_f = Concat(flat_P', flat_P'', F_face) │                          │
│  │      = [T_H×3 + T_H×3 + 16]              │                          │
│  │      = [T_H×6 + 16]                      │                          │
│  │                                           │                          │
│  │  With T_H=25: C_f ∈ R^{166}             │                          │
│  └─────────────────┬────────────────────────┘                          │
│                    │                                                    │
│                    ▼                                                    │
│  ┌──────────────────────────────────────────┐                          │
│  │  GATING MLP                               │                          │
│  │                                           │                          │
│  │  G = σ(W_2 · ReLU(W_1 · C_f + b_1) + b_2)                         │
│  │                                           │                          │
│  │  W_1: R^{166} → R^{128}  (hidden layer)  │                          │
│  │  W_2: R^{128} → R^{T_H×6} (output layer) │                          │
│  │  σ = sigmoid (output ∈ [0,1])             │                          │
│  │                                           │                          │
│  │  G ∈ R^{T_H × 6}                        │                          │
│  └─────────────────┬────────────────────────┘                          │
│                    │                                                    │
│                    ▼                                                    │
│  ┌──────────────────────────────────────────┐                          │
│  │  WEIGHTED COMBINATION                     │                          │
│  │                                           │                          │
│  │  Reshape G → [T_H, 6]                    │                          │
│  │  W'  = G[:, :3]    ∈ R^{T_H × 3}       │                          │
│  │  W'' = G[:, 3:]    ∈ R^{T_H × 3}       │                          │
│  │                                           │                          │
│  │  P̂ = W' ⊗ P' + W'' ⊗ P''               │                          │
│  │  (element-wise multiply + add)            │                          │
│  │                                           │                          │
│  │  Normalize: P̂ = P̂ / ||P̂||              │                          │
│  │  (ensure output is unit vector on sphere) │                          │
│  └─────────────────┬────────────────────────┘                          │
│                    │                                                    │
│                    ▼                                                    │
│  OUTPUT:                                                                │
│    P̂ [T_H, 3]  ← FINAL predicted head positions (3D unit vectors)    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Equations for Stage 5D

```
# Face embedding
F_face = ReLU(W_face · F_raw + b_face)                F_face ∈ R^{16}
  where F_raw = [FaceActivity, BrowLower_avg, JawDrop, EyesClosed_avg, BrowRaise_avg] ∈ R^5

# Concatenation
C_f = Concat(Flatten(P'), Flatten(P''), F_face)       C_f ∈ R^{T_H×6 + 16}

# Gating MLP
hidden = ReLU(W_1 · C_f + b_1)                        hidden ∈ R^{128}
G = σ(W_2 · hidden + b_2)                             G ∈ R^{T_H × 6}

# Split into weights for each prediction
W'  = Reshape(G)[:, :3]                               W' ∈ R^{T_H × 3}
W'' = Reshape(G)[:, 3:]                               W'' ∈ R^{T_H × 3}

# Weighted combination
P̂_raw = W' ⊗ P' + W'' ⊗ P''                         (element-wise multiplication)

# Normalize to unit sphere
P̂ = P̂_raw / ||P̂_raw||_2                             P̂ ∈ R^{T_H × 3},  ||P̂|| = 1
```

### Inputs & Outputs Summary

| | Shape | Description |
|--|-------|-------------|
| **Input: P'** | `[batch, T_H, 3]` | Trajectory prediction (from LSTM) |
| **Input: P''** | `[batch, T_H, 3]` | Content-aware prediction (from Temporal Attn) |
| **Input: face_raw** | `[batch, 5]` | Face features (5 blendshape values) |
| **Output: P̂** | `[batch, T_H, 3]` | FINAL predicted positions (unit vectors) |

### Intuition (Easy Language)

Imagine two advisors giving you directions:
- **Advisor 1 (P')**: "Based on which way you've been walking, you'll end up at the park."
- **Advisor 2 (P'')**: "There's a fire truck over there with sirens — you'll probably go look at it."

Now a third person looks at YOUR FACE:
- If you look surprised → "Trust Advisor 2 (the fire truck is attracting attention)"
- If you look bored → "Trust Advisor 1 (you're just walking your usual route)"
- If you look confused → "Trust Advisor 2 (you're searching for something)"

The gating MLP learns WHICH facial expressions mean "trust trajectory" vs "trust content."

---

# STAGE 5E: USER PERSONALIZATION EMBEDDING

## What it does (simple)

Different users behave differently. User #3 is an explorer who looks everywhere. User #7 always stares at the center. User #12 follows fast action.

The user embedding gives each user a "personality" that biases the LSTM from the very start.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              5E: USER EMBEDDING                       │
│                                                      │
│  user_id (integer, 0 to N-1)                        │
│      │                                               │
│      ▼                                               │
│  ┌───────────────────────┐                           │
│  │  nn.Embedding(N, 32)  │   N = number of users     │
│  │  Lookup table          │   32 = embedding dim      │
│  └───────────┬───────────┘                           │
│              │                                       │
│              ▼                                       │
│  u_k ∈ R^{32}   (user's learned personality vector) │
│              │                                       │
│       ┌──────┴──────┐                                │
│       ▼             ▼                                │
│  ┌──────────┐  ┌──────────┐                          │
│  │Linear_h  │  │Linear_c  │                          │
│  │32 → 128  │  │32 → 128  │                          │
│  │+ tanh    │  │+ tanh    │                          │
│  └────┬─────┘  └────┬─────┘                          │
│       │             │                                │
│       ▼             ▼                                │
│   h_0 ∈ R^128  c_0 ∈ R^128                          │
│   (initial hidden   (initial cell                    │
│    state for         state for                       │
│    LSTM_head)        LSTM_head)                      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### For New (Unseen) Users at Test Time

```
Option A (default): u_unknown = mean(u_1, u_2, ..., u_N)  ← average of all known users
Option B (if data available): Fine-tune u_new with 10 seconds of data
```

---

# STAGE 6: LOSS FUNCTION & TRAINING

## Loss Function: Geodesic Distance (Same as STAR-VP)

The loss measures the angular distance between predicted and actual head positions on the sphere.

```
For one sample:

L = (1/T_H) × Σ_{j=1}^{T_H}  arccos( clamp( ⟨P̂_j, P_j^{gt}⟩, -1, 1 ) )

where:
  P̂_j     = predicted head position at future timestep j  (3D unit vector)
  P_j^{gt} = actual head position at future timestep j    (3D unit vector)
  ⟨·,·⟩    = dot product
  arccos   = gives angle in radians (0 = perfect, π = worst)
  clamp    = prevents numerical issues with arccos at ±1

For a batch of B samples:
  L_batch = (1/B) × Σ_{b=1}^{B} L_b
```

### Why geodesic loss (not MSE)?

```
BAD: MSE in 3D:  L = ||P̂ - P^{gt}||²
  → This measures straight-line distance THROUGH the sphere
  → A point at (0,0,1) and (0,0,-1) are "far apart" by Euclidean distance
     but actually just 180° apart on the sphere

GOOD: Geodesic: L = arccos(⟨P̂, P^{gt}⟩)
  → This measures the angle ON the sphere surface
  → Geometrically correct for spherical data
  → Same loss STAR-VP uses
```

## Training Configuration

```
Optimizer:     Adam (lr = 1e-4, weight_decay = 1e-5)
Scheduler:     CosineAnnealingLR (T_max = 100 epochs, eta_min = 1e-6)
Batch size:    32
Max epochs:    100
Early stopping: patience = 10 epochs (stop if val loss doesn't improve)
Gradient clip:  max_norm = 1.0  (prevent exploding gradients)
```

## Training Procedure

```
For each epoch:
  For each batch in train_loader:
    1. Forward pass through MUSE-VP model
    2. Compute geodesic loss
    3. Backward pass (compute gradients)
    4. Clip gradients
    5. Optimizer step
    6. Log training loss
  
  After each epoch:
    7. Evaluate on validation set
    8. Save checkpoint if best validation loss
    9. Check early stopping
```

---

# STAGE 7: EVALUATION & ABLATION

## Evaluation Metrics

| Metric | What It Measures | Formula |
|--------|-----------------|---------|
| **Geodesic Error (°)** | Average angular error | `mean(arccos(⟨P̂, P^{gt}⟩)) × 180/π` |
| **Overlap Ratio** | Viewport overlap (like MFTR) | `area(predicted_VP ∩ actual_VP) / area(actual_VP)` |
| **Per-Horizon Error** | Error at each prediction step | Error at t+1s, t+2s, t+3s, t+4s, t+5s |

## Data Splits (Two Strategies)

### Video-Split (Cross-Video Generalization)
```
Train:  10 videos (all users)
Val:    2 videos (all users)
Test:   2 videos (all users)

Tests: "Can model predict on videos it never saw?"
```

### User-Split (Cross-User Generalization)
```
Train:  60% of users (all videos)
Val:    20% of users (all videos)
Test:   20% of users (all videos)

Tests: "Can model predict for users it never saw?"
For new users: use average user embedding
```

## Ablation Study

| # | Model Name | What's Active | Expected |
|---|-----------|---------------|----------|
| 0 | Linear Extrapolation | Just extend last velocity | Worst |
| 1 | LSTM-only | Single LSTM, head only | Baseline |
| 2 | STAR-VP (reproduced) | Head LSTM + PAVER + Spatial + Temporal + Gating | Our baseline |
| 3 | + Eye in LSTM | Add eye stream to LSTM | Better than 2 |
| 4 | + Eye-Head Offset | Add offset features to eye LSTM | Better than 3 |
| 5 | + Eye Spatial | Add eye gaze to Spatial Attention Q | Better than 4 |
| 6 | + Face Gating | Add face to Gating Fusion | Better than 5 |
| 7 | + User Embedding | Add personalization | Better than 6 |
| **8** | **MUSE-VP (full)** | **Everything** | **Best** |

---

# HYPERPARAMETERS REFERENCE TABLE

| Parameter | Symbol | Value | Reason |
|-----------|--------|-------|--------|
| Past window length | T_M | 25 frames (5s @ 5fps) | Same as STAR-VP |
| Future prediction length | T_H | 25 frames (5s @ 5fps) | Same as STAR-VP |
| Sampling rate | fps | 5 fps (downsampled) | Same as STAR-VP |
| Top-K saliency points | K | 32 | Same as STAR-VP |
| LSTM hidden dimension | hidden | 128 | Standard |
| LSTM layers | n_layers | 1 | Keep simple |
| User embedding dimension | d_u | 32 | Small (few users) |
| Face embedding dimension | d_f | 16 | Small (5 raw features) |
| Attention model dimension | d_model | 64 | Balance speed/quality |
| Attention heads | n_heads | 4 | Standard |
| Attention MLP dimension | d_ff | 256 | 4× d_model |
| Learning rate | lr | 1e-4 | Standard for Adam |
| Batch size | B | 32 | Fits in GPU memory |
| Max epochs | | 100 | With early stopping |

---

# IMPLEMENTATION PIPELINE (No Code — Just the Plan)

## Phase 1: Data Preprocessing (Week 1)

```
Files to create:
  muse_vp/data_preprocessing.py

Tasks:
  1.1  Parse your collected CSVs (head.csv, eye.csv, face.csv, combined.csv)
  1.2  Parse Wu_MMSys_17 head tracking CSVs (for STAR-VP baseline comparison)
  1.3  Align all tracking data to video frame timestamps
  1.4  Convert angles → 3D unit vectors
  1.5  Normalize all features
  1.6  Save as .pt files per participant per video
  1.7  Write unit tests to verify data quality
```

## Phase 2: Dataset & DataLoader (Week 1)

```
Files to create:
  muse_vp/dataset.py

Tasks:
  2.1  Create MUSEVPDataset class (PyTorch Dataset)
  2.2  Implement sliding window creation
  2.3  Implement train/val/test splits (video-split and user-split)
  2.4  Handle batching with DataLoader
  2.5  Verify shapes of all tensors in a batch
```

## Phase 3: Model Implementation (Week 2)

```
Files to create:
  muse_vp/models/
    __init__.py
    dual_lstm.py          ← Stage 5A
    spatial_attention.py   ← Stage 5B
    temporal_attention.py  ← Stage 5C (copy from STAR-VP)
    gating_fusion.py       ← Stage 5D
    user_embedding.py      ← Stage 5E
    muse_vp_model.py       ← Full model combining all modules

Tasks:
  3.1  Implement DualStreamLSTM (5A)
  3.2  Implement EyeGuidedSpatialAttention (5B)
  3.3  Port TemporalAttention from STAR-VP (5C)
  3.4  Implement FaceModulatedGating (5D)
  3.5  Implement UserEmbedding (5E)
  3.6  Implement MUSEVP (combines everything)
  3.7  Write a forward pass test with dummy data
```

## Phase 4: STAR-VP Baseline (Week 2)

```
Files to create:
  muse_vp/models/starvp_baseline.py

Tasks:
  4.1  Implement STAR-VP (head-only LSTM, original attention, original gating)
  4.2  This uses the SAME architecture but WITHOUT eye/face/user modifications
  4.3  Train and evaluate → these are your BASELINE numbers
```

## Phase 5: Training Script (Week 3)

```
Files to create:
  muse_vp/train.py

Tasks:
  5.1  Training loop with geodesic loss
  5.2  Validation evaluation after each epoch
  5.3  Checkpointing (save best model)
  5.4  Logging (tensorboard or wandb)
  5.5  Early stopping
  5.6  Configuration via YAML or argparse
```

## Phase 6: Evaluation Script (Week 3)

```
Files to create:
  muse_vp/evaluate.py

Tasks:
  6.1  Load trained model
  6.2  Compute geodesic error (overall and per-horizon)
  6.3  Compute overlap ratio
  6.4  Generate comparison tables
  6.5  Generate plots (error vs. prediction horizon)
```

## Phase 7: Ablation Study (Week 4)

```
Tasks:
  7.1  Train each ablation variant (rows 0-8 from ablation table)
  7.2  Evaluate all variants
  7.3  Create comparison table
  7.4  Analyze which components help most
  7.5  If something doesn't help → remove it from final model
```

---

# DATA FLOW SUMMARY (End to End)

```
RAW DATA
  Video (.mp4)  ──────────────────→  PAVER ──→ Saliency ──→ SalMap Proc ──→ S_xyz [T,32,3]
  head.csv  ──→ preprocess ──→ head_3d [T,3]                                  S_weight [T,32]
  eye.csv   ──→ preprocess ──→ eye_3d [T,3]
  combined  ──→ preprocess ──→ offset [T,3], fixation [T,2]
  face.csv  ──→ preprocess ──→ face [T,5]
  user_id   ──→ integer

           ↓ (sliding windows, batching)

ONE TRAINING SAMPLE
  head_3d[T_M,3] + eye_3d[T_M,3] + offset[T_M,3] + fixation[T_M,2]
  + S_xyz[T_H,32,3] + S_weight[T_H,32]
  + face[5] + user_id
  + target_head[T_H,3]

           ↓ (model forward pass)

STAGE 5A: Dual-Stream LSTM
  Input:  head_3d[T_M,3], eye_3d+offset+fix[T_M,8], user_id
  Output: P' [T_H, 3]

STAGE 5B: Eye-Guided Spatial Attention
  Input:  P'[T_H,3], S_xyz[T_H,32,3], S_weight[T_H,32], eye_gaze_3d[T_H,3]
  Output: S_{s-out}[T_H,32,d], P_{s-out}[T_H,d]

STAGE 5C: Temporal Attention
  Input:  P'[T_H,3], S_{s-out}, P_{s-out}
  Output: P'' [T_H, 3]

STAGE 5D: Face-Modulated Gating
  Input:  P'[T_H,3], P''[T_H,3], face[5]
  Output: P̂ [T_H, 3]  ← FINAL PREDICTION

LOSS:
  L = mean( arccos( dot(P̂, target_head) ) )
```

---

# WHAT MAKES THIS ARCHITECTURE PUBLISHABLE

```
╔════════════════════════════════════════════════════════════════════╗
║                     5 NOVEL CONTRIBUTIONS                          ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  1. EYE-HEAD OFFSET AS PREDICTIVE SIGNAL                ⭐⭐⭐   ║
║     No existing paper uses the DIFFERENCE between eye and head     ║
║     as a directional predictor. This is our strongest signal.      ║
║                                                                    ║
║  2. FACE-MODULATED GATING FUSION                        ⭐⭐⭐   ║
║     First paper to use facial expressions to control how           ║
║     trajectory vs. content predictions are weighted.               ║
║                                                                    ║
║  3. DUAL-STREAM ARCHITECTURE IN SPHERICAL SPACE         ⭐⭐     ║
║     Unlike MFTR (flat 2D tiles), we keep everything in 3D sphere  ║
║     coordinates with cos(φ) correction. Geometrically correct.    ║
║                                                                    ║
║  4. USER PERSONALIZATION EMBEDDINGS                      ⭐⭐     ║
║     First viewport prediction model with learned per-user          ║
║     behavior profiles that initialize the prediction.              ║
║                                                                    ║
║  5. FIRST HEAD+EYE+FACE DATASET FOR 360° VP             ⭐⭐⭐   ║
║     No public dataset has all three modalities collected           ║
║     synchronously from a modern VR headset.                        ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```
