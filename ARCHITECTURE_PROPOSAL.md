# MUSE-VP: Multi-Modal User-Specific Enhanced Viewport Prediction in 360° Videos

## Extending STAR-VP with Eye Tracking, Face Tracking, and Personalization

---

# PART 1: UNDERSTANDING THE ORIGINAL STAR-VP

## 1.1 What STAR-VP Does (Big Picture)

STAR-VP predicts **where a user will look in the future** in a 360° video. It takes two inputs:

1. **Content signal**: What's visually interesting in the video (saliency maps from PAVER)
2. **Motion signal**: Where the user's head has been pointing (past head trajectory)

And it outputs: **Predicted future head position** (yaw, pitch) for the next T_H timesteps.

## 1.2 STAR-VP Architecture (Original — From Figure 2 of the Paper)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STAR-VP ORIGINAL PIPELINE                          │
│                                                                             │
│  VIDEO V̄ ──→ [PAVER] ──→ S̄ (saliency) ──→ [SalMap Processor] ──→ S_xyz  │
│                                                                    │        │
│                                                                    ▼        │
│  PAST HEAD P̄_{t-T_M+1:t} ──→ [LSTM] ──→ P'_{t+1:t+T_H}                  │
│         (2D: yaw, pitch)        │              │                            │
│                                 │              │                            │
│                                 ▼              ▼                            │
│                         [Spatial Attention Module]                           │
│                           (Space-aligned fusion)                            │
│                                 │                                           │
│                                 ▼                                           │
│                    C_t (temporal concatenation)                              │
│                                 │                                           │
│                                 ▼                                           │
│                        [Temporal Attention Module]                           │
│                          (Time-varying fusion)                              │
│                                 │                                           │
│                                 ▼                                           │
│                      P''_{t+1:t+T_H}                                       │
│                                 │                                           │
│                    P' ──→ [Gating Fusion] ←── P''                          │
│                                 │                                           │
│                                 ▼                                           │
│                      P̂_{t+1:t+T_H} (FINAL PREDICTION)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1.3 STAR-VP Components (What Each Does)

### A. SalMap Processor
- **Input**: 2D saliency map S̄ ∈ R^{H×W} from PAVER
- **Process**: Converts each pixel to a 3D unit vector on the sphere using equirectangular-to-spherical projection
- **Output**: S_xyz ∈ R^{K×3} — the top-K most salient 3D locations on the sphere
- **Intuition**: Transforms "what's interesting" from a flat image into "where on the sphere is it interesting"

### B. LSTM Module
- **Input**: Past head positions P̄_{t-T_M+1:t} ∈ R^{T_M × 3} (3D unit vectors on sphere)
- **Process**: Standard LSTM that learns temporal patterns in head movement
- **Output**: Initial prediction P'_{t+1:t+T_H} ∈ R^{T_H × 3} (predicted future positions)
- **Intuition**: "Based on how the head has been moving, where will it go next?" — This is a MOTION-ONLY prediction (ignores video content)

### C. Spatial Attention Module
- **Inputs**: S_{s-in} (saliency features) and P_{s-in} (viewpoint features from LSTM)
- **Process**:
  - Encoder: Q=viewpoint, K=saliency, V=saliency → "Given where you're looking, what saliency is relevant?"
  - Decoder: Q=saliency, K=viewpoint, V=viewpoint → "Given what's salient, which viewpoints match?"
- **Outputs**: S_{s-out} (refined saliency) and P_{s-out} (refined viewpoint)
- **Intuition**: Aligns WHERE the user is heading with WHAT the video is showing, in 3D space

### D. Temporal Attention Module (First Fusion Stage)
- **Input**: Concatenation C_t along temporal dimension of spatial outputs + LSTM prediction + positional embeddings
- **Process**: Encoder-Decoder with cross-attention across time
- **Output**: P''_{t+1:t+T_H} (temporally refined prediction)
- **Intuition**: "How does the saliency-viewport relationship CHANGE over time?" — captures that saliency shifts and user attention follows

### E. Gating Fusion Module (Second Fusion Stage)
- **Input**: C_f = concatenation of P' (LSTM prediction) and P'' (attention prediction) along feature dimension
- **Process**: Flatten → Linear → ReLU → Linear → Sigmoid → produces weights W' and W''
- **Output**: P̂ = W' ⊗ P' + W'' ⊗ P'' (element-wise weighted combination)
- **Intuition**: "How much should I trust the motion-only prediction vs. the content-aware prediction?" — When content is boring, trust motion. When content is exciting, trust saliency.

### F. Encoder/Decoder Structure (Shared)
Both Encoder and Decoder use the standard Transformer block:
```
Input → LayerNorm → Multi-Head Attention → Residual + → LayerNorm → MLP → Residual + → Output
```
- Encoder uses self-attention (Q, K, V from same source)
- Decoder uses cross-attention (Q from one source, K/V from another)

---

# PART 2: WHAT'S MISSING IN STAR-VP (WHY WE NEED EYE + FACE)

## 2.1 The Fundamental Limitation

STAR-VP only knows WHERE the head is pointing. But:

> **The head is a LAGGING indicator. The eyes are a LEADING indicator.**

When a user wants to look at something:
1. **First** (0ms): The eyes move (saccade) — ~200-500°/s
2. **Then** (200-300ms later): The head follows — ~50-100°/s
3. **Finally** (after head settles): Eyes fine-tune (fixation)

STAR-VP is blind to steps 1 and 3. It only sees step 2, and by then the movement has already started.

## 2.2 What Eye Data Tells Us That Head Data Cannot

| Signal | What It Reveals | Prediction Horizon |
|--------|----------------|-------------------|
| Eye-head offset (GazeRelativeH/V) | **Direction** of upcoming head turn | 200-300ms ahead |
| Eye-head offset magnitude (EyeHeadOffset) | **Imminence** of head turn (large = turn coming) | 100-500ms ahead |
| IsFixating | Whether user found target (fixating) or searching (saccading) | Current state |
| FixationDurationMs | How engaged with current target (longer = more interested) | 500ms-2s ahead |
| Eye gaze direction (GazeYaw, GazePitch) | Precise attention point within viewport | Immediate |

## 2.3 What Face Data Tells Us

| Signal | What It Reveals | Use In Prediction |
|--------|----------------|-------------------|
| FaceActivity | Overall engagement level | High → saliency-driven; Low → trajectory-driven |
| Brow_Lowerer_L/R | Concentration/confusion | Confused → more exploratory movement |
| Jaw_Drop | Surprise/reaction | Surprise → may redirect to new event |
| Eyes_Look_Down/Left/Right/Up | Gaze direction validation | Cross-validates eye tracker |
| EyeClosedL/R | Blink detection | Blinks = brief attention gap |

## 2.4 The Key Insight: Eye-Head Offset Is a PREDICTIVE VECTOR

From your collected data (combined.csv):
- `GazeRelativeH`: Horizontal offset of eyes from head center (degrees)
- `GazeRelativeV`: Vertical offset of eyes from head center (degrees)
- `EyeHeadOffset`: Magnitude = sqrt(H² + V²)

**If GazeRelativeH = +5° (eyes looking right of head center):**
→ The head will rotate RIGHT within the next 200-300ms

**If EyeHeadOffset = 15° (large divergence):**
→ A head movement is IMMINENT

**If EyeHeadOffset = 2° (small divergence):**
→ The user is fixating, head is STABLE

This is literally a **direction vector** pointing where the head will go next. No other viewport prediction model has this signal.

---

# PART 3: PROPOSED ARCHITECTURE — MUSE-VP

## 3.1 Overview

We make **exactly 4 modifications** to STAR-VP. Everything else stays the same:

| # | Modification | Where | What Changes |
|---|-------------|-------|-------------|
| 1 | **Extended LSTM Input** | LSTM Module | Input goes from 3D → 11D (add eye + offset + fixation) |
| 2 | **Eye-Guided Spatial Attention** | Spatial Attention Module | Viewpoint query includes eye gaze direction |
| 3 | **Face-Modulated Gating** | Gating Fusion Module | Face features influence gating weights |
| 4 | **User Personalization** | LSTM Module | User embedding initializes LSTM hidden state |

### What STAYS THE SAME:
- ✅ PAVER (unchanged, frozen)
- ✅ SalMap Processor (unchanged)
- ✅ Temporal Attention Module (unchanged)
- ✅ Encoder/Decoder structure (unchanged)
- ✅ Loss function (unchanged — geodesic distance)
- ✅ Training procedure (same as STAR-VP)

## 3.2 Modified Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          MUSE-VP ARCHITECTURE                                    │
│                                                                                  │
│  VIDEO V̄ ──→ [PAVER] ──→ S̄ ──→ [SalMap Processor] ──→ S_xyz                  │
│                                                           │                      │
│                                                           ▼                      │
│  PAST HEAD P̄    ─┐                                                              │
│  (yaw, pitch)     │                                                              │
│                   ├──→ [EXTENDED LSTM] ──→ P'_{t+1:t+T_H}                       │
│  PAST EYE  Ē    ─┤      ↑                     │                                 │
│  (gaze yaw/pitch) │      │                     │                                 │
│                   │   [u_k]                    │                                 │
│  EYE-HEAD Ō     ─┤  (user                     │                                 │
│  (relH, relV,    │   embedding)                │                                 │
│   offset, fix)   ─┘                            │                                 │
│                                                ▼                                 │
│                              ┌────────────────────────────────┐                  │
│               S_xyz ───→     │ EYE-GUIDED SPATIAL ATTENTION   │                  │
│               E_gaze_3d ──→  │  Encoder: Q=[P;E_gaze], K=S   │                  │
│                              │  Decoder: Q=S, K=[P;E_gaze]   │                  │
│                              └────────────────────────────────┘                  │
│                                          │                                       │
│                                          ▼                                       │
│                              [TEMPORAL ATTENTION MODULE]                          │
│                              (UNCHANGED from STAR-VP)                            │
│                                          │                                       │
│                                          ▼                                       │
│                                   P''_{t+1:t+T_H}                               │
│                                          │                                       │
│                    ┌─────────────────────────────────────────┐                   │
│        P' ───→     │     FACE-MODULATED GATING FUSION       │                   │
│        P'' ──→     │  C_f = [P'; P''; F_face]               │                   │
│        F_face ──→  │  [W'; W''] = σ(MLP(C_f))              │                   │
│                    │  P̂ = W' ⊗ P' + W'' ⊗ P''              │                   │
│                    └─────────────────────────────────────────┘                   │
│                                          │                                       │
│                                          ▼                                       │
│                              P̂_{t+1:t+T_H} (FINAL)                             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

# PART 4: EACH MODIFICATION IN DETAIL

---

## Modification 1: Extended LSTM Module

### 4.1.1 Original STAR-VP

In the original STAR-VP, the LSTM receives only head position:

**Input**: P̄_{t-T_M+1:t} ∈ R^{T_M × 3}

where each timestep is a 3D unit vector (x, y, z) on the sphere representing head direction.

**Equation (STAR-VP Original)**:

```
h_0 = 0  (zero initial hidden state)
h_i, c_i = LSTM(p̄_i, h_{i-1}, c_{i-1})    for i = 1, ..., T_M
P'_{t+1:t+T_H} = Linear(h_{T_M})
```

### 4.1.2 Our Modification

We concatenate eye tracking features to the LSTM input at each timestep:

**New Input**: X_{t-T_M+1:t} ∈ R^{T_M × D_in}

where D_in = 11 and each timestep vector is:

```
x_i = [ p̄_i,           ← head direction (3D unit vector: x, y, z)
         ē_i,           ← eye gaze direction (3D unit vector: x, y, z)
         ō_H_i,         ← GazeRelativeH (horizontal eye-head offset, degrees)
         ō_V_i,         ← GazeRelativeV (vertical eye-head offset, degrees)
         ō_mag_i,       ← EyeHeadOffset (magnitude of offset, degrees)
         f_i,           ← IsFixating (0 or 1)
         d_i ]          ← FixationDurationMs (normalized to [0,1])
```

**Equation (MUSE-VP Extended)**:

```
x_i = Concat(p̄_i, ē_i, ō_i, f_i, d_i) ∈ R^{11}

h_0 = Linear_u(u_k)      ← user embedding initialization (Modification 4)
c_0 = 0

h_i, c_i = LSTM(x_i, h_{i-1}, c_{i-1})    for i = 1, ..., T_M
P'_{t+1:t+T_H} = Linear_out(h_{T_M})
```

### 4.1.3 Intuition — WHY This Works

**Think of it like driving a car:**
- STAR-VP (original): You can only see where the steering wheel is pointing → you guess where the car goes
- MUSE-VP (ours): You can see the steering wheel AND the driver's eyes AND their hands → you can predict turns BEFORE they happen

**Specifically:**

1. **Head direction p̄** tells you the CURRENT viewport center — same as original
2. **Eye gaze direction ē** tells you WHERE within the viewport attention is focused — the LSTM learns that if gaze drifts to the edge of the viewport, a head turn follows
3. **Eye-head offset ō** is a DIRECTION VECTOR pointing where the head will go:
   - Large positive ō_H → head will turn RIGHT
   - Large negative ō_H → head will turn LEFT
   - The LSTM learns this temporal relationship automatically
4. **IsFixating f** tells the LSTM the PHASE of eye movement:
   - Fixating (f=1): User found target, head is stable or slowly adjusting
   - Saccading (f=0): User is searching, head may move unpredictably
5. **FixationDuration d** tells STABILITY:
   - Long fixation → user is engaged, head stays put
   - Short fixation → user is scanning, head will move soon

**The LSTM will learn these patterns from data automatically.** We don't need to hard-code the rules — the LSTM discovers the eye-head temporal relationship during training.

### 4.1.4 Converting Angles to 3D Unit Vectors

Both head and eye data come as (yaw, pitch) in degrees. We convert to 3D unit vectors for consistency with STAR-VP's SalMap Processor:

```
Given yaw θ (degrees) and pitch φ (degrees):

x = cos(φ_rad) × sin(θ_rad)
y = sin(φ_rad)
z = cos(φ_rad) × cos(θ_rad)

where θ_rad = θ × π/180, φ_rad = φ × π/180
```

For the **head**: θ = EulerYaw, φ = EulerPitch (from head.csv)
For the **eye**: θ = GazeYaw, φ = GazePitch (from eye.csv)

### 4.1.5 Feature Table: Exact Columns Used

| Feature | Source CSV | Column Name | Dimension | Preprocessing |
|---------|-----------|-------------|-----------|---------------|
| Head direction | head.csv | EulerYaw, EulerPitch | 3 (after 3D conversion) | Convert to unit vector |
| Eye gaze direction | eye.csv | GazeYaw, GazePitch | 3 (after 3D conversion) | Convert to unit vector |
| Eye-head offset H | combined.csv | GazeRelativeH | 1 | Normalize to [-1, 1] by dividing by 30° |
| Eye-head offset V | combined.csv | GazeRelativeV | 1 | Normalize to [-1, 1] by dividing by 30° |
| Eye-head offset magnitude | combined.csv | EyeHeadOffset | 1 | Normalize to [0, 1] by dividing by 30° |
| Is fixating | eye.csv | IsFixating | 1 | Already binary (0 or 1) |
| Fixation duration | eye.csv | FixationDurationMs | 1 | Normalize: d / 1000 (cap at 1.0) |
| **Total per timestep** | | | **11** | |

---

## Modification 2: Eye-Guided Spatial Attention

### 4.2.1 Original STAR-VP

In the Spatial Attention Module, the viewpoint features serve as the Query to attend to saliency features:

**Original Encoder (cross-attention)**:
```
Q = Linear_Q(P_{s-in})     ← from viewpoint (head-only)
K = Linear_K(S_{s-in})     ← from saliency
V = Linear_V(S_{s-in})     ← from saliency

Attention = softmax(Q × K^T / √d_k) × V
```

This asks: "Given where the HEAD is pointing, what saliency features are spatially relevant?"

### 4.2.2 Our Modification

We enrich the Query with eye gaze information:

**Extended Encoder**:
```
E_gaze_3d = SphereProject(GazeYaw, GazePitch)    ← eye gaze as 3D point on sphere
P̂_{s-in} = Concat(P_{s-in}, E_gaze_3d)           ← enriched viewpoint features

Q = Linear_Q(P̂_{s-in})     ← from viewpoint + eye gaze
K = Linear_K(S_{s-in})      ← from saliency (unchanged)
V = Linear_V(S_{s-in})      ← from saliency (unchanged)

Attention = softmax(Q × K^T / √d_k) × V
```

**Extended Decoder** (reverse):
```
Q = Linear_Q(S_{s-in})      ← from saliency (unchanged)
K = Linear_K(P̂_{s-in})     ← from viewpoint + eye gaze
V = Linear_V(P̂_{s-in})     ← from viewpoint + eye gaze

Attention = softmax(Q × K^T / √d_k) × V
```

### 4.2.3 Intuition — WHY This Works

**Original STAR-VP spatial attention**: "The user's head is pointing at (θ_head, φ_head). What saliency is near that position?"

**Our extended spatial attention**: "The user's head is at (θ_head, φ_head) BUT their eyes are at (θ_eye, φ_eye). What saliency is near where the eyes are actually looking?"

**Why this is better:**

The head covers a ~100° field of view. Within that 100°, the user might be looking at very different things:
- Head pointing at a soccer field (center), but eyes fixated on the goalkeeper (right edge)
- Head pointing at a stage, but eyes tracking a specific dancer

With eye gaze as part of the Query, the Spatial Attention focuses on the EXACT salient region the user cares about, not just the general head direction. This makes the saliency-viewport alignment much more precise.

### 4.2.4 Implementation Detail

The Linear_Q layer's input dimension increases from d_P to d_P + 3:

```python
# Original STAR-VP
self.linear_q = nn.Linear(d_viewpoint, d_model)

# MUSE-VP (ours)
self.linear_q = nn.Linear(d_viewpoint + 3, d_model)  # +3 for eye gaze 3D vector
```

This is a ONE-LINE change to the Spatial Attention Module. The K and V projections remain unchanged.

---

## Modification 3: Face-Modulated Gating Fusion

### 4.3.1 Original STAR-VP

The Gating Fusion produces scalar weights for two predictions:

```
C_f = Concat_feature(P', P'')           ← concatenate along feature dimension

W = σ(Linear₂(ReLU(Linear₁(Flatten(C_f)))))

W' = W[:, :T_H×3]        ← weights for LSTM prediction
W'' = W[:, T_H×3:]       ← weights for attention prediction

P̂ = W' ⊗ P' + W'' ⊗ P''
```

This gate decides: "Trust the motion prediction or the content prediction?"

### 4.3.2 Our Modification

We add face engagement features as CONTEXT for the gating decision:

```
F_raw = [FaceActivity, Brow_Lowerer_avg, Jaw_Drop, Eyes_Closed_avg, BrowRaise_avg]

F_face = Linear_face(F_raw)   ← project face features to compact embedding, R^{d_f}

C_f = Concat_feature(P', P'', F_face)    ← face features provide context

W = σ(Linear₂(ReLU(Linear₁(Flatten(C_f)))))

W' = W[:, :T_H×3]
W'' = W[:, T_H×3:]

P̂ = W' ⊗ P' + W'' ⊗ P''
```

**Note**: Face features influence the GATE WEIGHTS, but the output is still a combination of P' and P''. The face doesn't produce its own prediction — it helps decide which prediction to trust.

### 4.3.3 Intuition — WHY This Works

**The gating question**: "Should I trust the trajectory prediction (P') or the saliency prediction (P'')?"

**Face features help answer this question:**

| Face State | What It Means | Gating Decision |
|-----------|---------------|-----------------|
| High FaceActivity | User is actively engaged/reacting | Trust saliency (P'') more — user is responding to content |
| Low FaceActivity | User is passive/bored | Trust trajectory (P') more — user is on autopilot |
| High Brow_Lowerer | Concentration/confusion | User is studying something — saliency matters |
| High Jaw_Drop | Surprise | Something unexpected happened — saliency may redirect attention |
| Eyes_Closed (blink) | Brief attention gap | Trust trajectory (P') — during blink, momentum continues |
| Brow raise | Interest/surprise | New stimulus — saliency matters more |

**Example:**
- Video shows a boring landscape → user's face is passive (low FaceActivity) → gate trusts trajectory prediction
- Suddenly a bird flies by → user's face shows surprise (Jaw_Drop, Brow_Raise) → gate shifts to trust saliency prediction

The gate LEARNS these relationships from data. We just provide the face signal; the MLP inside the gate learns what it means.

### 4.3.4 Feature Table: Face Features Used

| Feature | Source | Computation | Dimension |
|---------|--------|-------------|-----------|
| FaceActivity | combined.csv | Direct | 1 |
| Brow_Lowerer_avg | face.csv | (Brow_Lowerer_L + Brow_Lowerer_R) / 2 | 1 |
| Jaw_Drop | face.csv | Direct | 1 |
| Eyes_Closed_avg | face.csv | (Eyes_Closed_L + Eyes_Closed_R) / 2 | 1 |
| Brow_Raise_avg | face.csv | (Outer_Brow_Raiser_L + Outer_Brow_Raiser_R) / 2 | 1 |
| **Total** | | | **5** |

These 5 features go through Linear_face (5 → d_f, where d_f = 16) to produce a compact embedding before entering the gating MLP.

---

## Modification 4: User Personalization Embedding

### 4.4.1 Original STAR-VP

The LSTM starts with zero hidden state for all users:

```
h_0 = 0, c_0 = 0
```

This means the model treats ALL users identically at the start of each prediction window.

### 4.4.2 Our Modification

We add a learnable embedding for each user that initializes the LSTM:

```
u_k = Embedding(user_id_k)     ← u_k ∈ R^{d_u}, k = 1, ..., K users

h_0 = tanh(Linear_h(u_k))      ← initialize hidden state from user embedding
c_0 = tanh(Linear_c(u_k))      ← initialize cell state from user embedding
```

### 4.4.3 Intuition — WHY This Works

Different users have DIFFERENT viewing behaviors:
- **Explorer users**: Look around a lot, large head movements, follow peripheral events
- **Focused users**: Lock onto main action, small head movements, follow saliency closely
- **Passive users**: Drift slowly, mostly stay at equator, minimal engagement

By giving each user a learned embedding that initializes the LSTM, the model starts with a "personality" before even seeing any data. After training:
- Explorer users' embeddings will push the LSTM toward higher variance predictions
- Focused users' embeddings will push toward saliency-aligned predictions
- Passive users' embeddings will push toward center-biased predictions

### 4.4.4 Implementation

```python
# During training: user_id comes from the data
self.user_embedding = nn.Embedding(num_users, d_u)  # d_u = 32
self.user_to_h = nn.Linear(d_u, lstm_hidden_size)
self.user_to_c = nn.Linear(d_u, lstm_hidden_size)

# Forward pass
u = self.user_embedding(user_id)          # [batch, d_u]
h_0 = torch.tanh(self.user_to_h(u))      # [batch, hidden]
c_0 = torch.tanh(self.user_to_c(u))      # [batch, hidden]
```

### 4.4.5 For New Users (At Test Time)

Option A: Use the average embedding (mean of all user embeddings)
Option B: Fine-tune the embedding for a new user with a few seconds of their data
Option C: Use a "default" learnable embedding for unknown users

---

# PART 5: MATHEMATICAL FORMULATION (Complete)

## 5.1 Notation

| Symbol | Meaning | Shape |
|--------|---------|-------|
| V̄ | Input 360° video | T_V × 3 × H × W |
| S̄ | PAVER saliency maps | T_V × H_s × W_s |
| S_xyz | Processed saliency (3D sphere points) | T_V × K × 3 |
| P̄ | Past head trajectory (3D unit vectors) | T_M × 3 |
| Ē | Past eye gaze trajectory (3D unit vectors) | T_M × 3 |
| Ō | Eye-head offset features | T_M × 3 |
| F | Fixation features (IsFixating, Duration) | T_M × 2 |
| F_face | Face engagement features | 5 |
| u_k | User embedding for user k | d_u |
| P' | LSTM-predicted future viewpoints | T_H × 3 |
| P'' | Attention-refined future viewpoints | T_H × 3 |
| P̂ | Final predicted future viewpoints | T_H × 3 |

## 5.2 Step-by-Step Forward Pass

### Step 1: Content Processing (UNCHANGED)

```
S̄ = PAVER(V̄)                              ← Frozen pretrained, not modified
S_xyz = SalMapProcessor(S̄)                  ← Not modified
```

### Step 2: Extended LSTM Prediction (MODIFIED)

```
For each past timestep i ∈ {t-T_M+1, ..., t}:

  p̄_i = Sphere(HeadYaw_i, HeadPitch_i)     ← 3D head unit vector
  ē_i = Sphere(GazeYaw_i, GazePitch_i)      ← 3D eye unit vector
  ō_i = [GazeRelH_i/30, GazeRelV_i/30, EyeHeadOff_i/30]  ← normalized offset
  f_i = [IsFixating_i, min(FixDur_i/1000, 1)]              ← fixation features

  x_i = Concat(p̄_i, ē_i, ō_i, f_i)        ← R^{11}

u_k = UserEmbedding(user_id)
h_0 = tanh(W_h × u_k + b_h)
c_0 = tanh(W_c × u_k + b_c)

h_i, c_i = LSTM(x_i, h_{i-1}, c_{i-1})      for i = 1, ..., T_M

P' = Linear_out(h_{T_M})                     ← R^{T_H × 3}
```

### Step 3: Eye-Guided Spatial Attention (MODIFIED)

```
E_gaze_3d = Sphere(GazeYaw_t, GazePitch_t)   ← current eye gaze as 3D vector

P̂_{s-in} = Concat(P_{s-in}, E_gaze_3d)       ← enriched viewpoint features

--- Encoder (cross-attention) ---
Q_enc = W_Q × P̂_{s-in}                       ← query from viewpoint+eye
K_enc = W_K × S_{s-in}                        ← key from saliency
V_enc = W_V × S_{s-in}                        ← value from saliency

A_enc = softmax(Q_enc × K_enc^T / √d_k) × V_enc

--- Decoder (cross-attention) ---
Q_dec = W_Q' × S_{s-in}                       ← query from saliency
K_dec = W_K' × P̂_{s-in}                      ← key from viewpoint+eye
V_dec = W_V' × P̂_{s-in}                      ← value from viewpoint+eye

A_dec = softmax(Q_dec × K_dec^T / √d_k) × V_dec

S_{s-out} = LayerNorm(A_enc + S_{s-in})
P_{s-out} = LayerNorm(A_dec + P_{s-in})
```

### Step 4: Temporal Attention (UNCHANGED)

```
C_t = Concat_temporal(P', S_{s-out}, P_{s-out}, E)   ← same as STAR-VP

... Encoder-Decoder with positional embeddings ...

P'' = TemporalAttention(C_t)                          ← R^{T_H × 3}
```

### Step 5: Face-Modulated Gating Fusion (MODIFIED)

```
F_raw = [FaceActivity, BrowLower_avg, JawDrop, EyesClosed_avg, BrowRaise_avg]
F_face = Linear_face(F_raw)                            ← R^{d_f}

C_f = Concat_feature(Flatten(P'), Flatten(P''), F_face)

G = σ(W_2 × ReLU(W_1 × C_f + b_1) + b_2)            ← gating weights

W' = G[:T_H×3]                                        ← weight for LSTM pred
W'' = G[T_H×3:]                                       ← weight for attention pred

P̂ = W' ⊗ P' + W'' ⊗ P''                              ← final prediction
```

## 5.3 Loss Function (SAME as STAR-VP)

Geodesic distance on the sphere:

```
L = (1/T_H) × Σ_{j=1}^{T_H} arccos(⟨p̂_j, p_j⟩)
```

where ⟨·,·⟩ is the dot product between predicted and ground truth unit vectors, and arccos gives the angular distance in radians.

This is the same loss function as STAR-VP — we don't need to change it because our output format (3D unit vectors on sphere) is identical.

---

# PART 6: WHY THIS WILL IMPROVE OVER STAR-VP (Guaranteed)

## 6.1 Information Theory Argument

**Original STAR-VP input per timestep**: 3 numbers (head x, y, z)
**MUSE-VP input per timestep**: 11 numbers (head + eye + offset + fixation)

The additional 8 numbers are NOT noise — they contain CAUSALLY RELEVANT information:
- Eye position CAUSES head movement (eye leads head)
- Eye-head offset PREDICTS the direction of the next head movement
- Fixation state PREDICTS stability of the head

By providing more relevant information to the LSTM, the prediction MUST improve (assuming the model has sufficient capacity to learn from it, which LSTMs do).

## 6.2 Ablation Study Plan (Proving Each Component Helps)

| Model | LSTM Input | Spatial Q | Gating Context | User Embed |
|-------|-----------|-----------|----------------|-----------|
| STAR-VP (baseline) | Head only (3D) | Head only | P', P'' | None |
| + Eye LSTM | Head + Eye + Offset (11D) | Head only | P', P'' | None |
| + Eye Spatial | Head + Eye + Offset (11D) | Head + Eye | P', P'' | None |
| + Face Gating | Head + Eye + Offset (11D) | Head + Eye | P', P'', Face | None |
| MUSE-VP (full) | Head + Eye + Offset (11D) | Head + Eye | P', P'', Face | Yes |

Expected pattern: Each row improves over the previous one.

The first ablation (+ Eye LSTM) will show the LARGEST improvement because the eye-head offset is the strongest new signal.

## 6.3 Comparison with State-of-the-Art

| Model | Uses Head | Uses Eye | Uses Face | Uses Saliency | User Personalization |
|-------|----------|---------|----------|---------------|---------------------|
| Xu et al. (CVPR'18) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Li et al. (MM'19) | ✅ | ❌ | ❌ | ✅ | ❌ |
| TRACK (NeurIPS'20) | ✅ | ❌ | ❌ | ✅ | ❌ |
| STAR-VP (MM'24) | ✅ | ❌ | ❌ | ✅ | ❌ |
| **MUSE-VP (Ours)** | **✅** | **✅** | **✅** | **✅** | **✅** |

We are the ONLY model that uses eye tracking, face tracking, AND personalization. This data advantage alone should ensure competitive or better results.

---

# PART 7: DATA PREPROCESSING PIPELINE

## 7.1 Temporal Alignment

Your data is sampled at ~72Hz. Videos are at ~25-30fps. We need to align them:

```
For each video frame at time t_frame:
  1. Find the closest tracking sample at time t_track
  2. If |t_frame - t_track| < 1/(2 × 72) seconds: use that sample
  3. Otherwise: interpolate between the two nearest samples
```

## 7.2 Preprocessing Each Feature

```python
# Head trajectory
head_yaw = normalize_angle(EulerYaw)     # to [-180, 180]
head_pitch = normalize_angle(EulerPitch)  # to [-90, 90]
head_3d = sphere_project(head_yaw, head_pitch)  # to unit vector

# Eye gaze
gaze_yaw = GazeYaw                       # already in degrees
gaze_pitch = GazePitch                    # already in degrees
gaze_3d = sphere_project(gaze_yaw, gaze_pitch)  # to unit vector

# Eye-head offset (normalize to [-1, 1] range)
offset_h = GazeRelativeH / 30.0          # 30° is a reasonable max
offset_v = GazeRelativeV / 30.0
offset_mag = EyeHeadOffset / 30.0

# Fixation
is_fixating = IsFixating                  # already 0 or 1
fix_duration = min(FixationDurationMs / 1000.0, 1.0)  # cap at 1 second

# Face (averaged over last few frames for stability)
face_activity = FaceActivity
brow_lower = (Brow_Lowerer_L + Brow_Lowerer_R) / 2
jaw_drop = Jaw_Drop
eyes_closed = (Eyes_Closed_L + Eyes_Closed_R) / 2
brow_raise = (Outer_Brow_Raiser_L + Outer_Brow_Raiser_R) / 2
```

## 7.3 Window Creation

For each prediction sample:
```
Input window:  frames [t-T_M+1, t-T_M+2, ..., t]        (T_M past frames)
Target window: frames [t+1, t+2, ..., t+T_H]              (T_H future frames)

Each input frame has: [head_3d(3), gaze_3d(3), offset(3), fixation(2)] = 11 features
Each target frame has: [head_3d(3)] = 3 features (we predict head position only)
```

Typical values from STAR-VP paper:
- T_M = 5 seconds of past data (at 5fps after downsampling = 25 frames)
- T_H = 5 seconds of future prediction (at 5fps = 25 frames)

---

# PART 8: TRAINING STRATEGY

## 8.1 Training Setup

```
Optimizer: Adam (lr = 1e-4, weight_decay = 1e-5)
Scheduler: CosineAnnealingLR (T_max = 100 epochs)
Batch size: 32
Epochs: 100
Early stopping: patience = 10 epochs on validation loss
```

## 8.2 Data Split Strategy

Two approaches (do both, report both):

**Video-split** (generalization across videos):
- Train: 10 videos, Val: 2 videos, Test: 2 videos
- All users appear in all splits
- Tests: "Can the model predict on NEW videos?"

**User-split** (generalization across users):
- Train: 60% of users, Val: 20%, Test: 20%
- All videos appear in all splits
- Tests: "Can the model predict for NEW users?"
- For new users, use average user embedding or fine-tune with first 10 seconds

## 8.3 Training Order

1. First: Train STAR-VP baseline (head only) → establish baseline numbers
2. Then: Train MUSE-VP ablations one by one → show each component helps
3. Finally: Train full MUSE-VP → show best results

---

# PART 9: SUMMARY — WHAT TO IMPLEMENT

## Changes to STAR-VP Code (in order of importance)

### Change 1: Extended LSTM Input (MOST IMPACTFUL)
- **File**: LSTM module
- **What**: Change input dimension from 3 to 11
- **Lines of code**: ~10 lines changed
- **Expected improvement**: 10-20% reduction in prediction error

### Change 2: Eye-Guided Spatial Attention
- **File**: Spatial Attention module
- **What**: Expand Q projection input dimension by 3, concatenate eye gaze
- **Lines of code**: ~5 lines changed
- **Expected improvement**: 3-8% additional reduction

### Change 3: Face-Modulated Gating
- **File**: Gating Fusion module
- **What**: Add face feature embedding to gating input
- **Lines of code**: ~15 lines changed (new Linear layer + concatenation)
- **Expected improvement**: 2-5% additional reduction

### Change 4: User Embedding
- **File**: LSTM module initialization
- **What**: Add embedding lookup table and LSTM state initialization
- **Lines of code**: ~20 lines changed
- **Expected improvement**: 3-7% additional reduction (especially for user-split evaluation)

## Total Expected Improvement

Conservatively: **15-30% reduction in geodesic prediction error** over STAR-VP baseline.

This is based on:
- Eye data providing 200-300ms predictive advantage
- More precise spatial attention alignment
- Engagement-aware fusion
- User-specific behavior modeling

---

# PART 10: QUICK REFERENCE CARD

```
╔══════════════════════════════════════════════════════════════╗
║                    MUSE-VP vs STAR-VP                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  UNCHANGED:                                                  ║
║  ✓ PAVER (saliency generation)                              ║
║  ✓ SalMap Processor                                          ║
║  ✓ Temporal Attention Module                                 ║
║  ✓ Encoder/Decoder structure                                 ║
║  ✓ Loss function (geodesic distance)                         ║
║                                                              ║
║  MODIFIED:                                                   ║
║  ① LSTM: input 3D → 11D (add eye, offset, fixation)        ║
║  ② Spatial Attn: Q includes eye gaze direction              ║
║  ③ Gating: face features influence gate weights             ║
║  ④ LSTM init: user embedding → h_0, c_0                    ║
║                                                              ║
║  NEW DATA USED:                                              ║
║  • GazeYaw, GazePitch (eye direction)                       ║
║  • GazeRelativeH/V, EyeHeadOffset (eye-head offset)        ║
║  • IsFixating, FixationDurationMs (fixation state)          ║
║  • FaceActivity, Brow/Jaw/Eyes blendshapes (engagement)     ║
║  • User ID (personalization)                                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```
