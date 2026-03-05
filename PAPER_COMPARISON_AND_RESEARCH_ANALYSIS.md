# Complete Research Analysis: MFTR vs STAR-VP vs Our MUSE-VP
## + Audio Question, Dataset Publishability, and What Makes This Thesis-Worthy

---

# TABLE OF CONTENTS

1. [Paper 1: STAR-VP — What It Does](#1-star-vp)
2. [Paper 2: MFTR — What It Does](#2-mftr)
3. [Side-by-Side Comparison: STAR-VP vs MFTR](#3-comparison)
4. [Our MUSE-VP: What's Different and Better](#4-muse-vp)
5. [Honest Gap Analysis: What We Need to Improve](#5-gaps)
6. [The Audio Question: Should We Use It?](#6-audio)
7. [Which Combination: eye+head+face+audio vs eye+head+audio vs eye+head+face?](#7-combination)
8. [Should We Keep PAVER?](#8-paver)
9. [Is Our Dataset Publishable?](#9-dataset)
10. [Existing Similar Datasets](#10-existing-datasets)
11. [What Makes This Publishable as a Paper](#11-publishable)
12. [Final Recommendation](#12-recommendation)

---

# 1. STAR-VP — What It Does (Simple Language) {#1-star-vp}

## The Problem STAR-VP Solves

When you watch a 360° video, you can only see ~100° at a time (your viewport). Streaming the entire 360° in high quality wastes bandwidth. So the system needs to PREDICT where you'll look in the next 1-5 seconds and stream THAT part in high quality.

## How STAR-VP Works

STAR-VP combines two signals:
1. **Video saliency** (PAVER) → "What's interesting in the video right now?"
2. **Past head movement** → "Where has this user been looking?"

And predicts: **"Where will this user look in the next 1-5 seconds?"**

## STAR-VP Architecture (the 5 modules)

```
VIDEO → [PAVER] → Saliency → [SalMap Processor] → S_xyz (3D points)
                                                        ↓
HEAD TRAJECTORY → [LSTM] → P' (initial prediction)      ↓
                              ↓                          ↓
                    [Spatial Attention Module]  ← ← ← ← ←
                    (fuses head + saliency in 3D space)
                              ↓
                    [Temporal Attention Module]
                    (models how fusion changes over time)
                              ↓
                    P'' (refined prediction)
                              ↓
              P' → [Gating Fusion] ← P''
                    (weighted combination)
                              ↓
                    P̂ (final predicted viewport)
```

## STAR-VP's Key Innovations
1. **Spherical coordinate fusion**: Both saliency and head trajectory are in 3D sphere space
2. **Two-stage attention**: Spatial (WHERE on sphere) + Temporal (WHEN over time)
3. **Learned gating**: Automatically decides "trust trajectory or trust saliency?"
4. **Long-term prediction**: Works for 1-5 seconds ahead (most models fail after 1-2s)

## STAR-VP's Modalities
- ✅ Visual saliency (PAVER)
- ✅ Head trajectory
- ❌ Eye tracking
- ❌ Face tracking
- ❌ Audio
- ❌ User personalization

## STAR-VP's Weakness
**It ONLY uses head movement.** The head is SLOW — it lags 200-300ms behind the eyes. By the time the head starts turning, the brain already decided to move 300ms ago. STAR-VP misses this early signal entirely.

---

# 2. MFTR (Multimodal Fusion Transformer) — What It Does {#2-mftr}

*Paper: "Tile Classification Based Viewport Prediction with Multi-modal Fusion Transformer" — ACM Multimedia 2023*

## The Problem MFTR Solves

Same basic problem as STAR-VP (predicting where user will look), but MFTR identifies TWO specific weaknesses in ALL previous methods:

### Weakness 1: Trajectory prediction lacks robustness
Previous methods predict the exact (x, y) coordinates of where the head will point. But a TINY error in predicted coordinates → completely WRONG viewport selection.

**Example**: If predicted head position is off by just 5°, the selected viewport rectangle shifts significantly and might miss the actual viewing area entirely.

### Weakness 2: Simplistic modality fusion
Previous methods (including early STAR-VP-like approaches) just concatenate features from different modalities and hope the model figures it out. This is "mechanized" — it doesn't explicitly model HOW the modalities interact.

## How MFTR Solves These

### Solution 1: Tile Classification Instead of Trajectory Prediction

Instead of predicting "the head will be at (yaw=45°, pitch=10°)", MFTR classifies each tile as:
- **Interested** (the user will want to see this tile)
- **Not interested**

Then selects the viewport that contains the MOST "interested" tiles.

**Why this is more robust**: Even if some tile classifications are wrong, the overall viewport selection is still correct because it uses MAJORITY vote across tiles, not a single point.

### Solution 2: Transformer-based Multimodal Fusion

MFTR has 5 key components:

```
HEAD MOVEMENT → [LSTM] ─────→ Temporal Embeddings ─┐
                                                     ├→ [Temporal Transformer] → T_embed
EYE MOVEMENT  → [LSTM] ─────→ Temporal Embeddings ─┘
                                                     
VIDEO FRAMES  → [MobileNetV2] → [Visual Transformer] → V_embed

T_embed + V_embed → [Temporal-Visual Fusion Transformer] → Tile Classification
```

**Key insight**: MFTR uses SEPARATE encoding for head and eye movements, then fuses them with a transformer that learns the inter-modal relationships.

## MFTR's Modalities
- ✅ Visual content (MobileNetV2 backbone)
- ✅ Head trajectory (LSTM + Transformer)
- ✅ Eye gaze trajectory (LSTM + Transformer)
- ❌ Face tracking
- ❌ Audio
- ❌ User personalization
- ❌ Saliency maps (uses raw visual features instead)

## MFTR's Datasets
- **PVS-HM**: Head movement dataset for panoramic video
- **Xu-Gaze**: Eye gaze + head movement dataset

## MFTR's Weakness
1. **No pre-computed saliency**: Uses MobileNetV2 directly on video frames — less sophisticated than PAVER for 360° content
2. **No spherical geometry**: Works in flat 2D tile space, doesn't account for equirectangular distortion
3. **No personalization**: Treats all users the same
4. **No face data**: Misses engagement/emotional signals
5. **Tile-based output**: Less precise than continuous coordinate prediction for some applications

---

# 3. Side-by-Side Comparison: STAR-VP vs MFTR {#3-comparison}

| Aspect | STAR-VP | MFTR | Winner |
|--------|---------|------|--------|
| **Prediction approach** | Trajectory (continuous yaw, pitch) | Tile classification (binary per tile) | Depends on application |
| **Saliency method** | PAVER (state-of-art for 360°) | MobileNetV2 (not 360°-aware) | **STAR-VP** ✅ |
| **Coordinate system** | 3D sphere (spherical) | 2D flat (equirectangular tiles) | **STAR-VP** ✅ |
| **Head trajectory** | LSTM → 3D unit vectors | LSTM → embeddings | Similar |
| **Eye tracking** | ❌ None | ✅ LSTM-encoded | **MFTR** ✅ |
| **Modality fusion** | Spatial + Temporal attention + Gating | Transformer with modality tokens | Both good |
| **Temporal modeling** | Temporal Attention Module | Temporal Transformer | Similar |
| **Robustness** | Moderate (single-point prediction) | High (tile majority vote) | **MFTR** ✅ |
| **Long-term prediction** | Strong (1-5 seconds) | Moderate | **STAR-VP** ✅ |
| **Spherical distortion handling** | ✅ cos(φ) correction | ❌ None | **STAR-VP** ✅ |
| **User personalization** | ❌ | ❌ | Neither |
| **Face tracking** | ❌ | ❌ | Neither |
| **Audio** | ❌ | ❌ | Neither |
| **Published at** | 2024 | ACM MM 2023 | Similar quality |

## Key Takeaways

1. **STAR-VP is better at spatial modeling** — it operates in true 3D sphere space with distortion correction
2. **MFTR is better at multimodal fusion** — it already uses both head AND eye data
3. **Neither uses face, audio, or personalization** — this is our opportunity
4. **Neither model is clearly "best"** — they have complementary strengths

---

# 4. Our MUSE-VP: What's Different and ACTUALLY Better {#4-muse-vp}

## What we take from EACH paper

| From STAR-VP | From MFTR | NEW in MUSE-VP |
|-------------|-----------|----------------|
| PAVER saliency (better for 360°) | Eye gaze as input modality | Face tracking data |
| 3D sphere coordinates | Separate temporal encoding per modality | User personalization |
| Spatial Attention Module | Transformer-based fusion | Eye-head offset as predictive signal |
| Temporal Attention Module | | Audio-aware saliency weighting |
| Gating Fusion | | |

## What makes MUSE-VP genuinely novel (things NO paper has done)

### Novelty 1: Eye-Head Offset as a PREDICTIVE VECTOR ⭐⭐⭐
**No one has done this before.**

Both STAR-VP and MFTR treat eye and head as separate streams. They encode them independently and fuse them.

But we have a UNIQUE signal from our data: `GazeRelativeH`, `GazeRelativeV`, `EyeHeadOffset` — this is the **DIFFERENCE** between eye and head direction, computed at each timestep.

**Why this is powerful**: This offset is literally a DIRECTION VECTOR pointing where the head will move next:
- If eyes are 5° right of head center → head will turn right in ~200ms
- If offset magnitude is large (>10°) → a head turn is imminent
- If offset is small (<3°) → user is fixating, head is stable

**This is our #1 novel contribution and the strongest claim for the paper.**

### Novelty 2: Face-Modulated Gating ⭐⭐
**No viewport prediction paper uses face tracking.**

Face expressions tell us the user's COGNITIVE STATE:
- High FaceActivity + Surprise → user is reacting to content → trust saliency prediction
- Low FaceActivity → user is on autopilot → trust trajectory prediction
- Brow lowerer → concentration → user is studying current region, less likely to move

We use this to MODULATE the gating fusion weights — the face doesn't make its own prediction, it helps decide WHICH prediction to trust.

### Novelty 3: User Personalization via Learned Embeddings ⭐⭐
**Neither STAR-VP nor MFTR personalizes predictions.**

Different users behave VERY differently in VR:
- "Explorers" scan the entire scene
- "Focused" users lock onto the main action
- "Passive" users drift slowly near the equator

Our user embedding initializes the LSTM hidden state, giving each user a "starting personality" for predictions.

### Novelty 4: All modalities in 3D sphere space ⭐
Unlike MFTR which operates in flat 2D tile space, we keep EVERYTHING in spherical coordinates:
- Head trajectory → 3D unit vector
- Eye gaze → 3D unit vector
- Saliency → 3D via SalMap Processor

This is geometrically correct and avoids equirectangular distortion errors.

---

# 5. Honest Gap Analysis: What We Need to Improve {#5-gaps}

Let me be BRUTALLY honest about what's NOT better yet:

## Gap 1: MFTR's tile classification IS more robust than our trajectory prediction
MFTR's binary tile classification with majority voting is genuinely more robust than predicting a single (yaw, pitch) point.

**How we address this**: We can add a SECONDARY metric — after predicting the trajectory, we also compute the tile overlap ratio (like MFTR does) as an evaluation metric. This shows our model works for both streaming paradigms.

## Gap 2: MFTR has a proper Temporal Transformer for EACH modality
MFTR encodes head and eye movements with separate LSTMs, then mines temporal dependencies within each modality before fusing them.

We currently use a single Extended LSTM that takes all 11 features concatenated. This might be limiting.

**Potential improvement**: Use TWO parallel LSTMs:
```
LSTM_head: head_3d(3) → h_head
LSTM_eye:  eye_3d(3) + offset(3) + fixation(2) → h_eye

Then: h_combined = Concat(h_head, h_eye) → P'
```

This is more similar to MFTR's approach and gives each modality its own representation space.

**My recommendation**: Start with single Extended LSTM (simpler), if results aren't satisfying, switch to dual-LSTM as an ablation. Both should be tried.

## Gap 3: We haven't proven our claims yet
All the theoretical advantages need experimental validation. The ablation study in our proposal is essential.

---

# 6. The Audio Question: Should We Use It? {#6-audio}

## The Short Answer
**YES, but in a VERY SPECIFIC and LIMITED way.**

## The Science: Does Audio Actually Affect Viewport?

**YES — there is strong evidence:**

### Research Evidence:
1. **Spatial audio in VR creates attention bias**: When sound comes from a specific direction, users are 2-3x more likely to turn their head toward it (Doukhan et al., 2018; Morgado et al., 2018)
2. **Audio-visual attention**: Studies show that humans naturally orient toward sound sources, and this is even STRONGER in VR because there are no visual borders — you MUST turn to see (Hendrix & Barfield, 1996)
3. **Sound "anchoring"**: Conversational audio (speech) keeps users fixated on the speaker's location much longer than visual saliency alone (Xu et al., 2018)

### Real-world examples from YOUR videos:
- Basketball game: Crowd cheering from the left → users look left
- Spring Festival Gala: Singer on stage → users look at the singer even when visual activity is elsewhere
- Jungle Book: Narrator's voice → users look in the direction of the speaking character

## How to Actually Use Audio (Without Overcomplicating Things)

### What I RECOMMEND: Audio Saliency Map (Simple, Effective)

**Don't try to build a complex audio encoder.** Instead:

1. **Extract audio energy spectrum**: Use a simple spectrogram or mel-frequency analysis
2. **If video has spatial audio (ambisonics)**: Extract the DIRECTION of dominant sound source → this gives you a 3D direction vector
3. **If video has stereo/mono audio**: Extract audio ENERGY level → this tells you "something interesting is happening" but not WHERE

### Simplest implementation (recommended for thesis):

```
Audio Energy per frame → scalar value a_t ∈ [0, 1]

High audio energy → BOOST saliency weights (things are happening!)
Low audio energy → REDUCE saliency weights (quiet scene)

Modified saliency: S'_weight = S_weight × (1 + α × a_t)
```

This is just ONE scalar multiplication and adds almost zero complexity.

### More advanced (if you have time):

```
If spatial audio (ambisonics) available:
  Extract dominant sound direction: (yaw_audio, pitch_audio) per frame
  Convert to 3D point: A_xyz
  Add to Spatial Attention Module as additional Key
  
  Q = viewpoint + eye
  K = [saliency, audio_direction]   ← audio as extra spatial key
  V = [saliency, audio_direction]
```

### What I DON'T RECOMMEND:
- Building a full audio encoder (too complex, not enough data)
- Using audio as a separate LSTM stream (overkill)
- Trying to extract speech content/semantics (wrong task)

## The Wu_MMSys_17 Videos — Do They Have Spatial Audio?

The Wu_MMSys_17 dataset videos are standard YouTube 360° videos. Most have:
- **Stereo audio** (2 channels) — useful for energy level only
- Some might have **ambisonics** (4+ channels) — useful for spatial direction

**You can check with ffmpeg**:
```bash
ffprobe -show_streams -select_streams a video.mp4
```
If you see 4+ audio channels, it's likely ambisonics.

---

# 7. Which Combination? {#7-combination}

## The Three Options

### Option A: Eye + Head + Face + Audio (4 modalities)
```
Pros:
✅ Maximum information
✅ Strongest novelty claim ("first to combine all 4")
✅ Best theoretical performance

Cons:
❌ Most complex to implement
❌ Audio adds marginal value compared to eye-head offset
❌ More things can go wrong
❌ Harder to debug
❌ Need to justify WHY audio helps in ablation
```

### Option B: Eye + Head + Audio (3 modalities, no face)
```
Pros:
✅ Audio is interesting for the paper narrative
✅ Simpler than A

Cons:
❌ You lose face data — which is UNIQUE and NOVEL
❌ Audio alone is a weaker signal than face
❌ Less publishable (eye+head+audio is less novel than face)
```

### Option C: Eye + Head + Face (3 modalities, no audio) ⭐ RECOMMENDED
```
Pros:
✅ Uses your UNIQUE Meta Quest Pro data (face tracking)
✅ Face data is NOVEL — no one has used it for viewport prediction
✅ Eye-head offset is your STRONGEST signal
✅ Face-modulated gating is a CLEAN contribution
✅ Less complexity, still high novelty
✅ All data collected from same device at same time (synchronized)
✅ MUCH easier to implement and debug

Cons:
❌ Misses audio signal (but audio is weak compared to eye/face)
```

## My Strong Recommendation: **Option C (Eye + Head + Face)** 🏆

Here's why:

### Reason 1: The data quality argument
Your eye, head, and face data all come from the SAME Meta Quest Pro at the SAME timestamps. They are perfectly synchronized at ~72Hz. Audio comes from the video file at a different rate and would need separate alignment — more preprocessing, more potential for errors.

### Reason 2: The novelty argument
- Eye tracking for viewport prediction? Already done (MFTR, Xu et al. 2018)
- Audio for viewport prediction? Some work exists (Chao et al. 2020)
- **Face tracking for viewport prediction? NOBODY has done this.**

Face tracking is your UNIQUE contribution. It's what makes this paper different from everything else.

### Reason 3: The practical argument
You're building a thesis. You need it WORKING and VALIDATED. Adding audio means:
- Extracting audio features from videos (new preprocessing pipeline)
- Synchronizing with your 72Hz tracking data
- Designing how audio integrates into the model
- One more thing to debug

With eye+head+face, EVERYTHING comes from your CSVs. Clean, simple, synchronized.

### Reason 4: Audio as "future work"
In your paper, you write: "We note that audio features could further enhance prediction by providing spatial sound cues; we leave this exploration for future work." This is a PERFECTLY ACCEPTABLE statement in academic papers and gives you another research direction.

---

## BUT — If You Really Want Audio (Compromise)

If you insist on trying audio, here's the MINIMUM viable approach:

```python
# Extract audio energy per video frame (simple, no deep learning)
import librosa

audio, sr = librosa.load(video_path, sr=22050)
hop_length = sr // video_fps  # align to video frames
energy = librosa.feature.rms(y=audio, hop_length=hop_length)[0]
energy_normalized = energy / energy.max()  # [0, 1] per frame

# Use as a SINGLE scalar multiplier on saliency weights
# In the Gating Fusion Module:
audio_boost = 1.0 + 0.5 * audio_energy_t  # range [1.0, 1.5]
saliency_weight *= audio_boost
```

This adds ~10 lines of code total and can be done as an ablation experiment. No new model architecture needed.

---

# 8. Should We Keep PAVER? {#8-paver}

## ABSOLUTELY YES. Keep PAVER unchanged. ✅

### Reasons:

1. **PAVER is state-of-the-art for 360° saliency detection**
   - Designed specifically for equirectangular projection
   - Uses deformable ViT (handles distortion)
   - Pretrained on multiple 360° datasets

2. **MFTR uses MobileNetV2 — which is WORSE for 360° content**
   - MobileNetV2 was designed for normal flat images
   - It doesn't handle equirectangular distortion
   - It doesn't know about panoramic continuity (left edge = right edge)

3. **Replacing PAVER = retraining from scratch**
   - You'd need saliency ground truth (fixation maps) for training
   - PAVER is already trained and working

4. **PAVER is our baseline's component**
   - We extend STAR-VP, which uses PAVER
   - Changing PAVER changes the baseline, making comparison unfair

5. **Our contribution is DOWNSTREAM of PAVER**
   - We don't claim to improve saliency detection
   - We claim to improve viewport PREDICTION by adding eye + face data
   - These are SEPARATE contributions

### In your paper, you write:
> "We adopt the PAVER saliency detector (Yun et al., 2022) as our content analysis backbone, consistent with the STAR-VP baseline. Our contributions are orthogonal to the saliency detection method — any improved saliency detector could be substituted without architectural changes."

This is a STRONG statement because:
- It shows your model is modular
- It positions saliency detection as a replaceable component
- Your innovations (eye, face, personalization) work regardless of which saliency model is used

---

# 9. Is Our Dataset Publishable? {#9-dataset}

## The Honest Answer: **YES, with conditions** ✅

### What Makes Your Dataset UNIQUE

| Aspect | Your Dataset | Existing Datasets |
|--------|-------------|-------------------|
| **Device** | Meta Quest Pro | HTC Vive, Oculus Rift, SMI eye tracker |
| **Eye tracking** | Built-in eye tracker (~72Hz) | External eye tracker (varies) |
| **Face tracking** | ✅ 63 blendshapes | ❌ None |
| **Head tracking** | ✅ 6DoF at ~72Hz | ✅ But typically lower rate |
| **Simultaneous** | All 3 from same device at same timestamp | Separate devices |
| **Videos** | Wu_MMSys_17 (14 selected) | Various |
| **Users** | 16-32 planned | 48-59 typical |

### What makes it publishable:

1. **Face tracking data in VR is VERY rare**
   - Most datasets only have head + maybe eye
   - Face blendshapes during 360° video viewing is NOVEL data
   - Researchers studying engagement, emotion, attention in VR will want this

2. **Multimodal SYNCHRONIZED data**
   - Head, eye, AND face from the same device at the same timestamp
   - No cross-device calibration needed
   - Clean temporal alignment

3. **Meta Quest Pro is a MODERN device**
   - Most existing datasets were collected on older hardware (HTC Vive, Oculus DK2)
   - Your data represents current-generation VR headset capabilities

### What you need to do to make it publishable:

1. **Collect from at least 20-25 participants**
   - 16 is minimum, 25+ is comfortable
   - Include demographic diversity (age, gender, VR experience)

2. **Document EVERYTHING**:
   - Exact hardware specs
   - Software versions (Unity version, Meta XR SDK version)
   - Room setup, lighting, calibration procedure
   - Pre/post questionnaire content
   - Ethical approval / IRB / consent forms
   - Data format specification

3. **Quality checks**:
   - Report tracking accuracy/confidence per participant
   - Identify and flag low-quality sessions
   - Show basic statistics: viewing patterns, entropy, coverage

4. **Make it reproducible**:
   - Provide Unity project for data collection
   - Provide preprocessing scripts
   - Provide format documentation

---

# 10. Existing Similar Datasets {#10-existing-datasets}

## Datasets That Overlap With Yours

### A. PVS-HM (Panoramic Video Saliency with Head Movement) 
- **What**: Head movement trajectories for 76 panoramic videos
- **Users**: 58 participants  
- **Device**: HTC Vive
- **Data**: Head movement only (NO eye tracking, NO face)
- **Videos**: 76 diverse panoramic videos
- **Overlap with yours**: Head movement on panoramic videos
- **What's missing**: No eye tracking, no face data

### B. Xu-Gaze Dataset
- **What**: Eye gaze + head movement
- **Users**: ~45 participants
- **Device**: HTC Vive Pro Eye
- **Data**: Head movement + eye gaze
- **Videos**: ~208 panoramic images + some videos
- **Overlap with yours**: Eye gaze + head movement
- **What's missing**: No face data, different videos

### C. Wu_MMSys_17 (Your video source)
- **What**: Head movement traces for 18 videos
- **Users**: 48 participants
- **Device**: Oculus Rift DK2
- **Data**: Head orientation only
- **Overlap with yours**: SAME VIDEOS
- **What's missing**: No eye tracking, no face data, OLD hardware

### D. Sitzmann et al. (2018) 
- **What**: Eye and head tracking in VR
- **Users**: 169 participants
- **Device**: Desktop + eye tracker (NOT in VR headset)
- **Data**: Eye fixation + head movement
- **Videos**: Static 360° images (NOT videos)
- **What's missing**: No face, images only, not real VR viewing

### E. David et al. (2018) — Salient360!
- **What**: Head + eye in 360° video
- **Users**: 57 participants
- **Device**: HTC Vive + Tobii eye tracker
- **Data**: Head + eye gaze fixations
- **Videos**: 19 omnidirectional videos
- **What's missing**: No face, different videos

## How Your Dataset is Different

```
                        Head    Eye     Face    Modern HMD   Videos   Synced
                        Track   Track   Track                         Device
PVS-HM                  ✅      ❌      ❌      ❌ (Vive)     76       N/A
Xu-Gaze                  ✅      ✅      ❌      ❌ (Vive)     208*     N/A
Wu_MMSys_17              ✅      ❌      ❌      ❌ (DK2)      18       N/A
Sitzmann                 ✅      ✅      ❌      ❌ (Desktop)  0*       No
David/Salient360         ✅      ✅      ❌      ❌ (Vive)     19       No
─────────────────────────────────────────────────────────────────────────────
YOUR DATASET (MUSE-VP)   ✅      ✅      ✅      ✅ (Quest Pro) 14      ✅
```

* = images, not videos

**YOUR DATASET IS THE ONLY ONE WITH FACE TRACKING.** This alone makes it publishable and valuable.

### Why it matters that you use Wu_MMSys_17 videos:
- Wu_MMSys_17 already has head tracking from 48 users
- YOU collect eye + face + head from your 20+ users on the SAME videos
- Researchers can COMBINE both datasets for larger studies
- You can VALIDATE your head tracking against the original Wu_MMSys_17 data

---

# 11. What Makes This Publishable as a Paper {#11-publishable}

## A publishable paper needs 4 things:

### ✅ 1. NOVELTY (What's new?)

| Contribution | Novelty Level | Justification |
|-------------|---------------|---------------|
| Eye-head offset as predictive signal | ⭐⭐⭐ HIGH | No VP paper uses this derived signal |
| Face-modulated gating | ⭐⭐⭐ HIGH | First to use face expressions for VP |
| Personalized user embeddings for VP | ⭐⭐ MEDIUM | User embedding exists in RecSys, not VP |
| Multi-modal dataset (head+eye+face) | ⭐⭐⭐ HIGH | First dataset with all 3 in VR |
| Eye-guided spatial attention | ⭐⭐ MEDIUM | MFTR uses eye, but not in spatial attention |

**Total: 3 high-novelty + 2 medium-novelty contributions = PUBLISHABLE** ✅

### ✅ 2. MOTIVATION (Why should anyone care?)

**Practical motivation**: 360° video streaming needs bandwidth optimization → accurate VP saves bandwidth
**Scientific motivation**: Understanding how eyes, head, and facial expressions coordinate during VR viewing
**User experience motivation**: Better VP → less visual quality drops → better user experience

### ✅ 3. METHODOLOGY (Is it rigorous?)

To make it rigorous:
- Ablation study (prove each component helps)
- Multiple evaluation metrics (geodesic error, tile overlap, MAE at multiple horizons)
- Multiple baselines (STAR-VP, MFTR, simple LSTM, linear extrapolation)
- Video-split AND user-split evaluation
- Statistical significance tests

### ✅ 4. RESULTS (Does it work?)

This is what we haven't proven yet. But based on:
- MFTR already shows eye+head > head alone
- Eye-head offset is a STRONGER signal than raw eye gaze alone
- Face data adds information that doesn't exist in any other modality
- User embeddings are well-studied in other domains

**I'm confident we'll see improvement.** The eye-head offset alone should give significant gains.

## Target Venues

| Venue | Tier | Deadline | Fit |
|-------|------|----------|-----|
| ACM Multimedia (MM) | A* | April/May | ⭐⭐⭐ Perfect |
| IEEE VR | A | Oct/Nov | ⭐⭐⭐ Perfect |
| ACM NOSSDAV | B | March | ⭐⭐ Good |
| ACM MMSys | B | Dec | ⭐⭐⭐ Perfect |
| IEEE TMM (journal) | Q1 | Rolling | ⭐⭐⭐ Perfect |
| IEEE TVCG | A | Rolling | ⭐⭐ Good |

---

# 12. Final Recommendation {#12-recommendation}

## What to do RIGHT NOW:

### Architecture: MUSE-VP with Eye + Head + Face (Option C)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MUSE-VP FINAL ARCHITECTURE                        │
│                                                                         │
│  VIDEO → [PAVER ❄️] → S̄ → [SalMap Processor] → S_xyz                 │
│                                                        ↓                │
│                                                        ↓                │
│  HEAD (3D) ──┐                                         ↓                │
│  EYE (3D)  ──┤→ [EXTENDED LSTM] → P' ──→ [SPATIAL ATTENTION] ← S_xyz  │
│  OFFSET (3)──┤     ↑                          ↑                        │
│  FIXATION(2)─┘   [u_k]                    E_gaze_3d                    │
│                                                ↓                        │
│                                    [TEMPORAL ATTENTION]                  │
│                                                ↓                        │
│                                    P'' ──→ [FACE-MODULATED]             │
│           FACE (5) → [Linear] → F_face →  [GATING FUSION] ← P'        │
│                                                ↓                        │
│                                         P̂ (FINAL)                      │
│                                                                         │
│  🔑 KEY DIFFERENCES FROM STAR-VP:                                      │
│  ① LSTM input: 3D → 11D (eye+offset+fixation added)                   │
│  ② Spatial Attention Q: enriched with eye gaze direction               │
│  ③ Gating: face features modulate the gate weights                     │
│  ④ LSTM init: user embedding → h₀, c₀                                 │
│                                                                         │
│  🔑 KEY DIFFERENCES FROM MFTR:                                         │
│  ① Uses PAVER saliency (360°-aware) not MobileNetV2                   │
│  ② Operates in 3D sphere space, not flat 2D tiles                     │
│  ③ Uses eye-head OFFSET (derived signal), not raw eye gaze alone      │
│  ④ Uses face tracking (MFTR doesn't)                                  │
│  ⑤ Has user personalization (MFTR doesn't)                            │
│                                                                         │
│  ❄️ = Frozen (not trained), everything else is trained                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Audio: Skip for now, mention as future work

### PAVER: Keep unchanged ❄️

### Dataset: Collect from 25+ participants, document thoroughly, plan to release

### Paper positioning:
> "We present MUSE-VP, a Multi-modal User-Specific Enhanced approach to viewport prediction in 360° videos. Unlike prior work that relies solely on head trajectory and video saliency (STAR-VP) or head+eye trajectories without spatial awareness (MFTR), MUSE-VP introduces four key innovations: (1) eye-head offset as a predictive signal for upcoming head movements, (2) face expression-modulated fusion gating, (3) eye-guided spatial attention in spherical coordinates, and (4) learned user embeddings for personalized prediction. We also contribute a new multimodal dataset with synchronized head, eye, and face tracking from a Meta Quest Pro headset."

### Ablation table for the paper:

| Model | Head | Eye | Eye-Head Offset | Face | User Embed | Error (°) ↓ |
|-------|------|-----|-----------------|------|------------|-------------|
| Linear extrap. | ✅ | | | | | baseline |
| LSTM only | ✅ | | | | | - |
| STAR-VP (reprod.) | ✅ | | | | | - |
| MFTR (reprod.) | ✅ | ✅ | | | | - |
| MUSE-VP (a) | ✅ | ✅ | | | | - |
| MUSE-VP (b) | ✅ | ✅ | ✅ | | | - |
| MUSE-VP (c) | ✅ | ✅ | ✅ | ✅ | | - |
| **MUSE-VP (full)** | **✅** | **✅** | **✅** | **✅** | **✅** | **best** |

**Each row should improve over the previous one. If it doesn't, that component isn't helping and should be removed.**

---

## SUMMARY CARD

```
╔════════════════════════════════════════════════════════════════╗
║                    FINAL DECISIONS                              ║
╠════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Architecture:  MUSE-VP (extends STAR-VP)         ✅             ║
║  Saliency:      PAVER (frozen, unchanged)         ✅             ║
║  Modalities:    Head + Eye + Face (NO audio)      ✅             ║
║  Audio:         Skip → future work                ✅             ║
║  Personalization: User embeddings                 ✅             ║
║  Dataset:       Publish (head+eye+face, Quest Pro) ✅            ║
║                                                                  ║
║  NOVEL CONTRIBUTIONS:                                            ║
║  1. Eye-head offset as predictive signal          ⭐⭐⭐        ║
║  2. Face-modulated gating fusion                  ⭐⭐⭐        ║
║  3. Eye-guided spatial attention (3D sphere)      ⭐⭐          ║
║  4. User personalization embeddings               ⭐⭐          ║
║  5. First head+eye+face dataset for 360° VP       ⭐⭐⭐        ║
║                                                                  ║
║  BETTER THAN STAR-VP because:                                    ║
║  → Has eye data (200-300ms predictive advantage)                ║
║  → Has face data (engagement-aware fusion)                      ║
║  → Has personalization (user-specific behavior)                 ║
║                                                                  ║
║  BETTER THAN MFTR because:                                       ║
║  → Uses PAVER (360°-aware saliency) not MobileNetV2             ║
║  → Operates in 3D sphere (geometrically correct)                ║
║  → Uses eye-head OFFSET (stronger than raw gaze)                ║
║  → Has face tracking + personalization (MFTR has neither)       ║
║                                                                  ║
╚════════════════════════════════════════════════════════════════╝
```
