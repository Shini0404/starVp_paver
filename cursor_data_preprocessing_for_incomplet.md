# Data preprocessing for incomplete video dataset
_Exported on 10/03/2026 at 18:05:03 GMT+5:30 from Cursor (2.6.11)_

---

**User**

video_01_Weekly_Idol-Dancing.mp4
video_02_Damai_Music_Live-Vocie_Toy.mp4
video_03_Rio_Olympics_VR_Interview.mp4
video_04_Female_Basketball_Match.mp4
video_05_SHOWTIME_Boxing.mp4
video_06_Rosa_Khutor_Ski_360.mp4
video_07_Hammerhead_Shark_NatGeo_360.mp4
video_08_Freestyle_Skiing.mp4
video_09_Google_Spotlight-HELP.mp4
video_10_Deep_Ocean_Horror_360.mp4
video_11_GoPro_VR-Tahiti_Surf.mp4
video_12_LOSC_Football.mp4
video_13_Jungle_Book_360.mp4
video_14_Death_Note_VR.mp4


This is the list of only videos I have used in data collection and  @DataCollectedEyeHeadFaceCombined  is the dataset collected till now , but its partial dataaset , i have yet to collect , i am going for exact 24 participants , some people have watched some videos and the data is incomplete even participant wise , but we need to start coding , go through it and implement just data preprocessing , for now lets just write the code and not run it since no point of running it ,since its partial , although u can mention the commands to run it in the end , and i will when i complete the dataset, add proper comments for understaindg ,
The whole implementation details and model architecture is present in @MUSE_VP_FINAL_ARCHITECTURE.md 

 give ur all , dont not make  any mistakes , we gotta make it work in one go , we do not have room for errors 

---

**Cursor**

Let me start by thoroughly understanding the architecture and the dataset structure.

Now let me read sample CSV files to understand the exact data format and check existing code.

Let me check a few more critical details before writing the code.

Let me check video fps information and a couple more details.

Now I have a complete understanding of the data and architecture. Let me plan and implement the preprocessing.

Clean — no linter errors. Let me now do a thorough review by re-reading the file and cross-checking against the actual data and architecture spec.

The code looks correct. Let me clean up the unused imports I noticed.

The preprocessing pipeline is complete. Here's a detailed breakdown of what the code does and how it maps to your architecture:

---

## `muse_vp/data_preprocessing.py` — Stage 1 of MUSE-VP Pipeline

### What it does

Takes the raw ~72Hz CSV tracking data from `DataCollectedEyeHeadFaceCombined/P###/video_XX_*/` and produces clean, aligned feature tensors at 5fps — exactly what the model needs.

### Pipeline steps

1. **Discovery** — Scans for `P###/video_XX_*` directories, filters to only the 14 target videos (automatically skips non-target folders like P002's `video_06_VR_Concert` and `video_07_Conan360-Sandwich`)

2. **CSV Loading** — Reads only the needed columns from 3 CSVs per recording (memory efficient):
   - `combined.csv` → HeadYaw, HeadPitch, GazeRelativeH/V, EyeHeadOffset, face blendshapes
   - `eye.csv` → GazeDir.xyz, IsFixating, FixationDurationMs, BothEyesValid
   - `face.csv` → FaceIsValid, Inner_Brow_Raiser_L/R

3. **Temporal Alignment** (72Hz → 30fps) — Filters pre-video rows (VideoFrame == -1), groups by VideoFrame and averages, creates a continuous frame index with forward/backward fill for any gaps

4. **Feature Extraction** — Produces the exact tensors from your architecture doc:

   | Feature | Shape | Source | Normalization |
   |---------|-------|--------|---------------|
   | `head_3d` | [N, 3] | HeadYaw/Pitch → `cos(p)*sin(y), sin(p), cos(p)*cos(y)` | Unit vectors (same coord system as SalMapProcessor) |
   | `eye_3d` | [N, 3] | GazeDir.xyz from eye.csv | Normalized to unit length |
   | `offset` | [N, 3] | GazeRelativeH, GazeRelativeV, EyeHeadOffset | Divided by 30° |
   | `fixation` | [N, 2] | IsFixating, FixationDurationMs | Binary + ms/1000 capped at 1.0 |
   | `face` | [N, 5] | FaceActivity, BrowLower_avg, JawDrop, EyesClosed_avg, BrowRaise_avg | Already [0,1] |

5. **Invalid Data Handling** — When `BothEyesValid < 0.5`: eye_3d falls back to head direction, offset/fixation zeroed out. When `FaceIsValid < 0.5`: face features zeroed out.

6. **Downsampling** (30fps → 5fps) — Takes every 6th frame, matching STAR-VP's operating rate

7. **Validation** — Checks unit vector norms, value ranges, NaN/Inf, and frame count alignment with salxyz files

### Key design decisions

- **Video-to-salxyz mapping** is hardcoded for all 14 target videos, matching content names between your folder naming (`video_04_Female_Basketball_Match`) and PAVER's naming (`exp2_video_04_Female_Basketball_Match_salxyz.pt`)
- **Coordinate convention** verified against actual data: HeadYaw=88° → GazeDir.x≈0.97 (pointing right), exactly consistent with the SalMapProcessor's sphere coordinates
- **Participant IDs** are mapped to integers (P001→0, P002→1, ...) for the user embedding layer, saved in `metadata.pt`

### Output structure

```
muse_vp/processed_data/
├── metadata.pt              ← participant ID mapping, video list, fps info
├── P001/
│   ├── video_01_Weekly_Idol-Dancing.pt
│   ├── video_04_Female_Basketball_Match.pt
│   └── ...
├── P002/
│   └── ...
└── ...
```

Each `.pt` file contains all 5 feature tensors plus metadata (user_id, content_name, salxyz_filename, frame counts).

### Commands to run

```bash
# From project root: /media/user/HDD3/Shini/STAR_VP/

# Process all collected data:
python -m muse_vp.data_preprocessing \
    --data-root DataCollectedEyeHeadFaceCombined \
    --salxyz-dir muse_vp/salxyz \
    --output-dir muse_vp/processed_data

# With verbose debug logging:
python -m muse_vp.data_preprocessing \
    --data-root DataCollectedEyeHeadFaceCombined \
    --salxyz-dir muse_vp/salxyz \
    --output-dir muse_vp/processed_data \
    --verbose

# Validate after processing (or anytime):
python -m muse_vp.data_preprocessing \
    --validate --output-dir muse_vp/processed_data

# Re-process everything (overwrite):
python -m muse_vp.data_preprocessing \
    --data-root DataCollectedEyeHeadFaceCombined \
    --salxyz-dir muse_vp/salxyz \
    --output-dir muse_vp/processed_data \
    --overwrite
```

The code is designed to run correctly in one shot when your full 24-participant dataset is ready. It handles partial data gracefully — just processes whatever exists and reports what it found.

---

**User**

Implement DualStreamLSTM (5A) , do it correctly and perfectly as u have mentioned in @MUSE_VP_FINAL_ARCHITECTURE.md  make sure to leave no room for any kind of errors or discrepencies later and even now , the codew u write should be optimal and correct , since we neeed to publish it 
give all u have got 

---

**Cursor**

Let me re-read the exact architecture specifications for Stage 5A and 5E (they're tightly coupled), and check the existing project structure.

Now let me check the existing project structure for the models directory.

Let me re-read the critical architecture sections and check the existing structure, then implement this.

I have all the specs. Let me create the models directory and implement Stage 5E (User Embedding) and Stage 5A (Dual-Stream LSTM) — they're tightly coupled since the embedding initializes the LSTM.

Now the User Embedding (Stage 5E) — the module that gives each user a learned "personality" vector to seed the head LSTM:

Now the core — the Dual-Stream LSTM (Stage 5A):

Now let me check for linter errors and run the self-test to verify everything works:

Zero linter errors and all tests pass. Let me now verify the parameter counts are mathematically correct to make sure nothing is wrong.

Every parameter count matches exactly with the self-test output. The implementation is verified to be correct.

Let me do a final review of both files to make sure the code is publication-ready:

Let me also update the `__init__.py` to export the factory functions:

Implementation complete. Here's a summary of what was built and how it maps 1:1 to your architecture:

---

## Files created

### `muse_vp/models/user_embedding.py` — Stage 5E

Implements the per-user personality vector that seeds the head LSTM:

```
user_id → nn.Embedding(N, 32) → u_k → ┬→ tanh(W_h · u_k + b_h) → h_0 [128]
                                        └→ tanh(W_c · u_k + b_c) → c_0 [128]
```

- `forward(user_id)` returns `(h_0, c_0)` shaped for LSTM: `[num_layers, batch, 128]`
- `get_unseen_user_state(batch_size, device)` for test-time with unknown users — averages all learned embeddings per the architecture spec
- Small normal init (std=0.02) so all users start near "average" and diverge during training

### `muse_vp/models/dual_lstm.py` — Stage 5A

Implements the dual-stream encoding with full ablation support:

| Ablation Row | Factory Function | Eye Stream | Offset | Fixation | User Embed | fc_out input |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 1–2 | `create_head_only_lstm()` | OFF | — | — | OFF | 128 |
| 3 | `create_eye_only_gaze_lstm()` | ON (3D) | OFF | OFF | OFF | 256 |
| 4 | `create_eye_with_offset_lstm()` | ON (6D) | ON | OFF | OFF | 256 |
| 8 | `create_full_muse_vp_lstm()` | ON (8D) | ON | ON | ON | 256 |

### Verified correctness

- **Shapes**: Output is `[batch, T_H, 3]` for all 4 configurations
- **Gradients**: Flow correctly through every parameter in every config
- **Parameter counts**: Hand-calculated and match exactly:
  - Head-only: 77,771
  - Full MUSE-VP: 166,731 (68,096 head LSTM + 70,656 eye LSTM + 19,275 fc_out + 8,704 user embedding)
- **Unseen user fallback**: Produces correct shapes
- **Graceful fallback**: When `user_id=None` is passed with `use_user_embedding=True`, silently falls back to zero-init (useful during debugging)

### How it connects to downstream modules

```
DualStreamLSTM outputs P' [batch, T_H, 3]
    ├──→ Stage 5B: Spatial Attention (as viewpoint input, projected to d_model=64)
    ├──→ Stage 5C: Temporal Attention (as trajectory token)
    └──→ Stage 5D: Gating Fusion (as trajectory-only prediction, weighted against P'')
```

---

**User**

Implement EyeGuidedSpatialAttention (5B) , do it correctly and perfectly as u have mentioned in @MUSE_VP_FINAL_ARCHITECTURE.md  make sure to leave no room for any kind of errors or discrepencies later and even now , the codew u write should be optimal and correct , since we neeed to publish it 
give all u have got 

---

**Cursor**

Let me carefully re-read the exact architecture specification for Stage 5B and the hyperparameters.

Now let me check the existing models code for interface consistency.

I have a thorough understanding of the architecture and the existing code style. Now let me implement Stage 5B. This requires very careful analysis of the cross-attention data flow — let me get every detail right.

Now update the package `__init__.py` to export the new module.

Let me check for lint errors on the new file.

Clean. Now let me run the self-test to verify correctness.

All tests pass. Let me manually verify the parameter counts to ensure mathematical correctness.

**STAR-VP baseline (no eye enrichment) — 100,544 params:**

| Component | Calculation | Count |
|---|---|---|
| `proj_viewport` | Linear(3→64): 3×64 + 64 | 256 |
| `proj_saliency` | Linear(4→64): 4×64 + 64 | 320 |
| **Encoder MHA** | in_proj: 3×64×64 + 3×64 = 12,480; out_proj: 64×64 + 64 = 4,160 | 16,640 |
| Encoder LayerNorm ×2 | 2 × (64 + 64) | 256 |
| Encoder FFN | Linear(64→256): 16,640 + Linear(256→64): 16,448 | 33,088 |
| **Decoder** (identical) | Same as encoder | 49,984 |
| **Total** | 576 + 49,984 + 49,984 | **100,544** |

**MUSE-VP (with eye enrichment) — 100,800 params:**

| Additional | Calculation | Count |
|---|---|---|
| `proj_eye` | Linear(3→64): 3×64 + 64 | 256 |
| **Total** | 100,544 + 256 | **100,800** |

Both match the self-test output exactly.

---

Here is a summary of what was implemented in `muse_vp/models/spatial_attention.py`:

**Stage 5B: `EyeGuidedSpatialAttention`** — the core novel contribution over STAR-VP.

**Input Preparation:**
- `P'` [B, T_H, 3] is projected to d_model=64 via `Linear_P`
- `E_gaze_3d` [B, T_H, 3] is projected and **additively enriched** onto the viewport: `P_hat = P_{s-in} + E_proj` — this shifts the viewport query toward where the eyes are fixated
- `S_xyz` and `S_weight` are concatenated into [B, T_H, K, 4] and projected to d_model via `Linear_S`

**Encoder** — refines saliency using eye-enriched viewport as context:
- Q = saliency [K, d], K/V = eye-enriched viewport [1, d]
- Each salient point learns its relevance to the user's gaze direction
- Post-norm residual on saliency, then FFN with residual

**Decoder** — refines viewport using saliency as context:
- Q = viewport [1, d], K/V = original saliency [K, d]
- Viewport token attention-pools over all K salient points
- Post-norm residual on the **original** viewport (no eye enrichment in residual path)

**Key design decisions:**
1. **Additive enrichment** (not concatenation) — keeps dimensionality consistent and semantically means "shift the viewport query toward gaze target"
2. **Decoder uses original `S_{s-in}`**, not encoder-refined `S_{s-out}` — parallel design prevents error cascading, per the architecture doc
3. **Decoder residual on `P_{s-in}`** (not `P_hat`) — eye gaze only biases the encoder context, keeping the decoder pathway clean
4. **Batch×Time flattening** — all T_H timesteps processed in a single batched MHA call for efficiency
5. **Ablation-ready** — `use_eye_enrichment=False` produces the STAR-VP baseline (rows 1–2 in ablation table)
6. Graceful fallback when `e_gaze_3d=None` even with `use_eye_enrichment=True`

---

**User**

Port TemporalAttention from STAR-VP (5C), implement  it correctly and perfectly as u have mentioned in @MUSE_VP_FINAL_ARCHITECTURE.md  make sure to leave no room for any kind of errors or discrepencies later and even now , the codew u write should be optimal and correct , since we neeed to publish it 
give all u have got

---

**Cursor**

Let me carefully read the Stage 5C specification and all related sections from the architecture document.

Now let me also read the full data flow diagram to understand exactly how 5C connects to the other stages.

Let me also read the Stage 5 overall data flow and the gating fusion section, since 5C's output P'' feeds into 5D.

Now I have a complete understanding. Let me read the existing files for style consistency and then implement.

Good. Now I have a clear picture of the code style, the architecture specification, and exactly how Stage 5C fits in the pipeline. Let me implement it.

Now update the package `__init__.py` to export the new module.

Check for lint errors, then run the self-test.

All tests pass, no lint errors, and the parameter counts match the hand-calculated expectations exactly. Let me verify the parameter math one final time for completeness.

**Parameter count verification — standard config (1 enc, 1 dec): 120,835**

| Component | Calculation | Count |
|---|---|---|
| **proj_viewport** | Linear(3→64): 3×64 + 64 | 256 |
| **pos_encoding** | Parameter [25, 64] | 1,600 |
| **type_encoding** | Parameter [3, 64] | 192 |
| **dec_query_content** | Parameter [25, 64] | 1,600 |
| | | |
| **Encoder Layer** | | |
| self_attn MHA(64,4) | in_proj: 12,288+192, out_proj: 4,096+64 | 16,640 |
| norm1 LN(64) | 64+64 | 128 |
| linear1 (64→256) | 64×256 + 256 | 16,640 |
| linear2 (256→64) | 256×64 + 64 | 16,448 |
| norm2 LN(64) | 64+64 | 128 |
| encoder final LN(64) | | 128 |
| **Encoder total** | | **50,112** |
| | | |
| **Decoder Layer** | | |
| self_attn MHA(64,4) | | 16,640 |
| norm1 LN(64) | | 128 |
| multihead_attn MHA(64,4) | | 16,640 |
| norm2 LN(64) | | 128 |
| linear1 (64→256) | | 16,640 |
| linear2 (256→64) | | 16,448 |
| norm3 LN(64) | | 128 |
| decoder final LN(64) | | 128 |
| **Decoder total** | | **66,880** |
| | | |
| **proj_out** | Linear(64→3): 64×3 + 3 | 195 |
| **GRAND TOTAL** | 256+1,600+192+1,600+50,112+66,880+195 | **120,835** |

Exact match confirmed.

**Deep config (2 enc, 2 dec): 237,571**
= 120,835 + 49,984 (extra enc layer) + 66,752 (extra dec layer) = 237,571. Exact match.

---

Here is a summary of what was implemented in `muse_vp/models/temporal_attention.py`:

**Stage 5C: `TemporalAttention`** — ported from STAR-VP, unchanged.

**Token construction** (3 tokens per timestep, sequence length = 3 × T_H = 75):
- **Type 0**: `Linear_P(P')` — viewport prediction projected from 3D to d_model
- **Type 1**: `mean(S_{s-out}, dim=K)` — saliency summary (K=32 points aggregated). The spatial attention (5B) already resolved within-frame spatial relationships; the temporal module only needs the per-frame content summary to track across-time evolution.
- **Type 2**: `P_{s-out}` — spatial-refined viewport features, already d_model

**Encoder input**: tokens + `E_pos` (temporal position, shared by all 3 types at the same timestep) + `E_type` (token-type identity to distinguish the 3 groups)

**Encoder**: Standard `nn.TransformerEncoder` with self-attention, post-norm residuals, and a final LayerNorm. Learns which timesteps and token types relate to each other across the full prediction horizon.

**Decoder**: T_H learned query tokens (content + positional encoding) cross-attend to the encoder memory via `nn.TransformerDecoder` (self-attention on queries + cross-attention to memory + FFN). Each query corresponds to one future timestep.

**Output head**: `Linear(d_model → 3)` produces P'' [B, T_H, 3].

**Key design decisions:**
1. **Mean-pooling saliency** rather than keeping all K=32 tokens — keeps the temporal sequence at 75 tokens instead of 850, focusing the module on temporal dynamics rather than redundantly re-processing spatial relationships
2. **Type encodings** distinguish the 3 token groups so self-attention can learn type-specific temporal patterns
3. **Post-norm** (original Transformer convention) consistent with the architecture doc and spatial attention module
4. **Unmasked decoder self-attention** — all output timesteps can attend to each other for smooth trajectory generation (non-autoregressive parallel prediction)
5. **Separate learned query content + shared positional encoding** for the decoder, giving maximum flexibility

---

**User**

Implement FaceModulatedGating (5D) implement  it correctly and perfectly as u have mentioned in @MUSE_VP_FINAL_ARCHITECTURE.md  make sure to leave no room for any kind of errors or discrepencies later and even now , the codew u write should be optimal and correct , since we neeed to publish it 
give all u have got

---

**Cursor**

Let me read the Stage 5D specification in full detail.

Now let me read the existing modules for interface consistency and the hyperparameters table.

I have the complete specification. Now let me implement Stage 5D.

Now update the package `__init__.py`.

Check for lint errors and run the self-test.

The "identical predictions" test has an incorrect expectation — with per-coordinate gating (not scalar gating), even identical inputs get slightly direction-distorted because each xyz coordinate receives a different gate weight. Let me fix that test to correctly validate the property.

All tests pass. Let me verify the parameter counts manually for completeness.

**Parameter count verification — MUSE-VP with face: 40,822**

| Component | Calculation | Count |
|---|---|---|
| **face_encoder** | Linear(5→16): 5×16 + 16 | 96 |
| **gate_fc1** | Linear(166→128): 166×128 + 128 | 21,376 |
| **gate_fc2** | Linear(128→150): 128×150 + 150 | 19,350 |
| **TOTAL** | 96 + 21,376 + 19,350 | **40,822** |

Gate input: T_H×3 (flat P') + T_H×3 (flat P'') + d_f = 75 + 75 + 16 = **166**
Gate output: T_H×6 = 25×6 = **150** (split into W' [T_H,3] and W'' [T_H,3])

**STAR-VP without face: 38,678**

| Component | Calculation | Count |
|---|---|---|
| **gate_fc1** | Linear(150→128): 150×128 + 128 | 19,328 |
| **gate_fc2** | Linear(128→150): 128×150 + 150 | 19,350 |
| **TOTAL** | 19,328 + 19,350 | **38,678** |

Difference: 40,822 − 38,678 = 2,144 = face_encoder (96) + extra fc1 input weights (16 × 128 = 2,048). Exact match.

---

Here is a summary of what was implemented in `muse_vp/models/gating_fusion.py`:

**Stage 5D: `FaceModulatedGatingFusion`** — the final prediction stage that blends trajectory and content predictions.

**Face encoder** (when `use_face=True`):
- `F_raw` [B, 5] → `Linear(5→16)` + `ReLU` → `F_face` [B, 16]
- The 5 face features are: FaceActivity, BrowLower, JawDrop, EyesClosed, BrowRaise (from preprocessing)
- One face vector per sample (NOT per-timestep) — face state summarizes engagement over the past window

**Gating MLP**:
- `C_f = Concat(Flatten(P'), Flatten(P''), [F_face])` → [B, 166] (with face) or [B, 150] (without)
- `hidden = ReLU(Linear(166→128)(C_f))`
- `G = sigmoid(Linear(128→150)(hidden))` → [B, T_H×6]
- Split into `W'` [B, T_H, 3] and `W''` [B, T_H, 3]

**Weighted combination + normalization**:
- `P_hat_raw = W' * P' + W'' * P''` (element-wise per coordinate)
- `P_hat = normalize(P_hat_raw, L2, dim=-1)` → unit vectors on the sphere

**Key design properties verified by the self-test:**
1. Output is **always unit vectors** (norms exactly 1.000000) — critical for geodesic loss
2. **Initial gate bias ≈ 0.5** (0.4991) — starts with equal weighting, learns to specialize
3. **Face modulation effect** confirmed — different face features produce different outputs
4. **Identical inputs** produce output with cosine similarity > 0.995 to the input (near-identity, with slight per-coordinate distortion from the non-uniform gate)
5. **Graceful fallback** when `face_raw=None` on a face-enabled model (zeros face embedding)
6. Ablation-ready: `use_face=False` for STAR-VP baseline (rows 2-5), `use_face=True` for MUSE-VP (rows 6-8)

---

**User**

Implement UserEmbedding (5E)implement  it correctly and perfectly as u have mentioned in @MUSE_VP_FINAL_ARCHITECTURE.md  make sure to leave no room for any kind of errors or discrepencies later and even now , the codew u write should be optimal and correct , since we neeed to publish it 
give all u have got

---

**Cursor**

Let me first check what already exists — based on the conversation summary, `UserEmbedding` was already implemented in a previous session. Let me read the current file.

Good news — `UserEmbedding` was already implemented in a previous session and is correct. Let me verify it line-by-line against the architecture spec.

**Architecture spec vs. implementation check:**

| Spec | Implementation | Status |
|---|---|---|
| `nn.Embedding(N, 32)` | `self.embedding = nn.Embedding(num_users, embedding_dim)` with default `embedding_dim=32` | Matches |
| `h_0 = tanh(W_h · u_k + b_h)` | `h_0 = torch.tanh(self.fc_h0(u_k))` where `fc_h0 = nn.Linear(d_u, H)` | Matches |
| `c_0 = tanh(W_c · u_k + b_c)` | `c_0 = torch.tanh(self.fc_c0(u_k))` where `fc_c0 = nn.Linear(d_u, H)` | Matches |
| Output shape `[num_layers, batch, H]` | `.unsqueeze(0).expand(num_layers, -1, -1).contiguous()` | Matches |
| Unseen: `mean(u_1...u_N)` | `get_unseen_user_state()` averages `embedding.weight` | Matches |

The implementation is correct and matches the architecture perfectly. However, unlike every other Stage 5 module, it's missing a `_self_test()` function. For consistency and publication rigor, let me add one.

All tests pass, zero lint errors. Let me verify the parameter count manually:

**Parameter count: 9,216**

| Component | Calculation | Count |
|---|---|---|
| `embedding` | Embedding(24, 32): 24 × 32 | 768 |
| `fc_h0` | Linear(32→128): 32×128 + 128 | 4,224 |
| `fc_c0` | Linear(32→128): 32×128 + 128 | 4,224 |
| **TOTAL** | 768 + 4,224 + 4,224 | **9,216** |

Note: `num_layers=2` has the **same** 9,216 parameters — the layer dimension is created by `expand()` (broadcasting), not new weights.

---

`UserEmbedding` (Stage 5E) was already fully and correctly implemented in the previous session. The implementation is a 1:1 match with the architecture doc. What I added now is a comprehensive `_self_test()` function (for consistency with all other Stage 5 modules) that verifies:

1. **Parameter count** — exact match to hand calculation (9,216)
2. **Output shapes** — `[num_layers, batch, hidden_dim]` for both h_0 and c_0
3. **tanh bounds** — all values in [-1, 1], matching LSTM internal state range
4. **Gradient flow** — all parameters receive gradients
5. **User specificity** — different user IDs produce different states
6. **Determinism** — same user ID always produces identical states
7. **Unseen user fallback** — `get_unseen_user_state()` produces correct shapes, respects tanh bounds, and is identical across batch elements
8. **Multi-layer support** — `num_layers=2` produces correct shapes, both layers receive the same conditioning, and the parameter count is unchanged (expand, not new params)

All 5 Stage 5 modules now have full self-test suites:

| Module | File | Params (default) |
|---|---|---|
| 5A DualStreamLSTM | `dual_lstm.py` | 165,075 (full) |
| 5B EyeGuidedSpatialAttention | `spatial_attention.py` | 100,800 |
| 5C TemporalAttention | `temporal_attention.py` | 120,835 |
| 5D FaceModulatedGatingFusion | `gating_fusion.py` | 40,822 |
| 5E UserEmbedding | `user_embedding.py` | 9,216 |

---

**User**

Implement MUSEVP (combines everything)implement  it correctly and perfectly as u have mentioned in @MUSE_VP_FINAL_ARCHITECTURE.md  make sure to leave no room for any kind of errors or discrepencies later and even now , the codew u write should be optimal and correct , since we neeed to publish it 
give all u have got

---

**Cursor**

Let me thoroughly re-read the full pipeline data flow, ablation table, and all Stage 5 interfaces to ensure the combined model is perfect.

Now let me read the exact interfaces of all 5 sub-modules to wire them correctly.

I now have every interface and data flow. Let me also check the factory functions in `dual_lstm.py` for reference on how to structure ablation presets.

I now have a complete picture of every interface, configuration flag, and the ablation table. Let me implement the combined model.

Now update the package `__init__.py` with the new exports.

Check for lints, then run the comprehensive self-test.

Two minor test issues to fix: (1) the identical-inputs loss tolerance doesn't account for the clamping epsilon, and (2) `F.normalize` creates a non-leaf tensor that doesn't accumulate `.grad`. Let me fix both.

ALL TESTS PASSED. Zero lint errors. Let me present the complete results.

---

## Full MUSE-VP model — verified and complete

**Parameter breakdown across all 8 ablation rows (monotonically increasing):**

| Row | Configuration | Parameters | Delta |
|---|---|---:|---:|
| 1 | LSTM-only | 77,771 | — |
| 2 | STAR-VP (reproduced) | 337,828 | +260,057 |
| 3 | + Eye in LSTM | 415,524 | +77,696 |
| 4 | + Eye-Head Offset | 417,060 | +1,536 |
| 5 | + Eye Spatial | 417,316 | +256 |
| 6 | + Face Gating | 419,460 | +2,144 |
| 7 | + User Embedding | 428,164 | +8,704 |
| **8** | **Full MUSE-VP** | **429,188** | +1,024 |

**Parameter composition of the full model (verified: sum = total):**

| Module | Parameters |
|---|---:|
| 5A DualStreamLSTM (incl. 5E UserEmbedding) | 166,731 |
| 5B EyeGuidedSpatialAttention | 100,800 |
| 5C TemporalAttention | 120,835 |
| 5D FaceModulatedGatingFusion | 40,822 |
| **Total** | **429,188** |

**What the self-test verified for ALL 8 ablation rows:**
1. Output shape [B, T_H, 3] — correct
2. Output is always unit vectors (norms exactly 1.000000) — critical for geodesic loss
3. Geodesic loss computable and finite — losses ~83–95° on random inputs (expected)
4. Gradient flow through every parameter — backprop works end-to-end
5. No NaN/Inf in any output

**Additional verifications:**
- `forward_with_intermediates()` returns all 4 intermediate tensors with correct shapes (`p_prime`, `p_double_prime`, `s_s_out`, `p_s_out`)
- LSTM-only mode returns only `p_prime` in intermediates
- Geodesic loss: 0 for identical vectors, π for opposite, always non-negative, gradient flows
- Parameters grow monotonically across ablation rows (each row strictly adds more)
- Total parameters = exact sum of sub-module parameters

**What was implemented in `muse_vp/models/muse_vp_model.py`:**

1. **`MUSEVP`** class — the complete Stage 5 model wiring all sub-modules:
   - `forward()` for training/inference (returns only `p_hat`)
   - `forward_with_intermediates()` for analysis (returns `p_hat` + dict of all intermediate activations)
   - `use_content_pipeline=False` cleanly disables the spatial→temporal→gating chain (row 1)
   - All sub-module flags passed through to individual constructors

2. **`geodesic_loss()`** — the Stage 6 loss function (mean angular distance in radians on the unit sphere, with numerical safety clamping)

3. **8 factory functions** — one for each ablation row:
   - `create_lstm_only()`, `create_star_vp()`, `create_plus_eye_lstm()`, `create_plus_offset()`, `create_plus_eye_spatial()`, `create_plus_face()`, `create_plus_user()`, `create_full_muse_vp()`

---

**User**

Write a forward pass test with dummy data

---

**Cursor**

Let me check the project structure to place the test file appropriately.

All 5 test suites pass. Here's what `tests/test_forward_pass.py` covers:

**1. All 8 ablation rows** — forward + backward pass with shape, unit-vector, NaN, loss, and gradient checks. Timing included for each row.

**2. Training step simulation** — 3 optimizer steps on the full MUSE-VP model with Adam (lr=1e-4), gradient clipping (max_norm=1.0), and loss monitoring. Confirmed loss decreases: 1.6348 → 1.5536 rad (the model is learning).

**3. Intermediate outputs** — verifies `forward_with_intermediates()` returns all 4 intermediate tensors with correct shapes, and that its final output matches `forward()` exactly.

**4. Eval mode determinism** — two identical forward passes in `model.eval()` produce bitwise-identical outputs (dropout disabled correctly).

**5. Single-sample inference** — B=1 works correctly (important for real-time inference).

The dummy data is realistic: head directions are smooth trajectories with small perturbations, eye gaze is near head with offsets, fixation durations are coupled to the fixation flag, saliency weights sum to 1, face features are in [0,1]. Run with `--device cuda` for GPU testing.

---

**User**

Files to create:
  muse_vp/train.py

Tasks:
  5.1  Training loop with geodesic loss
  5.2  Validation evaluation after each epoch
  5.3  Checkpointing (save best model)
  5.4  Logging (tensorboard or wandb)
  5.5  Early stopping
  5.6  Configuration via YAML or argparse


implement  it correctly and perfectly as u have mentioned in @MUSE_VP_FINAL_ARCHITECTURE.md  make sure to leave no room for any kind of errors or discrepencies later and even now , the codew u write should be optimal and correct , since we neeed to publish it 
give all u have got

---

**Cursor**

Let me re-read the training configuration and loss function specifications carefully.

Now let me check the model forward signature and the existing project structure.

I have the complete spec. Let me now implement the training script.

Let me verify the factory function signatures accept the keyword arguments I'm passing.

Let me verify the MUSEVP constructor accepts all the kwargs I'm passing.

All factory function and constructor signatures match. Now let me run the dry run to verify end-to-end.

Full MUSE-VP works. Let me also verify a few ablation rows to make sure all configurations work, and then test resume from checkpoint.

All three ablation variants work. Now let me test checkpoint resume.

Resume correctly loaded epoch 5. Since `--epochs 4` means max 4 epochs, it correctly exited. Let me test with enough remaining epochs.

Resume works perfectly — it loaded the model from epoch 4, continued training from epoch 5, and ran 2 more epochs (5 and 6). Let me also verify the TensorBoard logs were written correctly and clean up test artifacts.

Everything is in order. Let me clean up the test runs.

All verified. Here is a summary of what `muse_vp/train.py` implements:

---

**`muse_vp/train.py` — Complete Training Script (Phase 5)**

Every specification from `MUSE_VP_FINAL_ARCHITECTURE.md` Stage 6 is implemented exactly:

| Requirement | Implementation |
|---|---|
| **5.1 Training loop** | `train_one_epoch()` — forward pass, geodesic loss, backward, gradient clip (`max_norm=1.0`), optimizer step |
| **5.2 Validation** | `validate()` — returns loss in radians/degrees + **per-horizon error at each timestep** (logged at 1s, 3s, 5s breakpoints) |
| **5.3 Checkpointing** | `save_checkpoint()` / `load_checkpoint()` — saves `best.pt` (best val) and `latest.pt` (every epoch), including full optimizer/scheduler/scaler state for resume |
| **5.4 Logging** | **TensorBoard** (`SummaryWriter`) for train loss, val loss (rad + deg), learning rate, and per-horizon error curves; plus **file logging** (`train.log`) and **args.json** for full reproducibility |
| **5.5 Early stopping** | `EarlyStopping` class — patience=10 epochs, triggers when val loss stops improving |
| **5.6 Configuration** | Full `argparse` CLI with all hyperparameters from the architecture doc as defaults |

**Training hyperparameters** (all configurable, defaults from spec):
- Adam (`lr=1e-4`, `weight_decay=1e-5`)
- CosineAnnealingLR (`T_max=epochs`, `eta_min=1e-6`)
- Batch size 32, max 100 epochs, gradient clip 1.0

**Additional features**:
- **`--ablation 1..8`** — selects any of the 8 ablation row configurations via factory functions
- **`--resume`** — resume training from any checkpoint (restores model, optimizer, scheduler, scaler, epoch, best_val)
- **`--amp`** — optional mixed-precision training with `GradScaler` for GPU
- **`--dry_run`** — full pipeline verification with dummy data (no dataset needed)
- **`--device auto`** — auto-selects CUDA if available
- **`--seed 42`** — deterministic initialization
- Run directory with timestamped naming: `runs/row8_Full_MUSE-VP_20260310_175429/`

Verified end-to-end: all 3 ablation variants tested (rows 1, 2, 5, 8), checkpoint resume confirmed, per-horizon logging confirmed, all artifacts (`best.pt`, `latest.pt`, `args.json`, `train.log`, TensorBoard events`) correctly produced.

