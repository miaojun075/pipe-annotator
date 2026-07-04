# PipeAnnotator 🔧

**Industrial Pipe Fitting Recognition System** — 工业管件智能识别系统

Automatically detect, classify, and measure pipe fittings from photos. Built for construction material quality inspection and inventory management.

从照片自动检测、分类、测量管件规格。面向建材质检与库存管理场景。

---

## 📸 What It Does

| Feature | Description |
|---------|-------------|
| **Auto Detection** | FastSAM segmentation + Otsu fallback for all pipe fitting types |
| **Multi-level Classification** | CNN (MobileNetV2) → DN area lookup → NCC template → SKU output |
| **Closed-loop Learning** | User corrections feed back into gallery, calibration, and SKU overrides |
| **YOLO Export** | Automatic polygon (segment) + bbox annotation export for model training |
| **Batch Processing** | Process hundreds of images with progress tracking |

### Supported Categories (38 types)

- **Galvanized**: Tee, Reducing Tee, Elbow 90°, Union, Internal Thread Straight (DN15-DN65)
- **Steel**: Tee, Reducing Tee, Elbow 90° (DN32-DN89)
- **Wall Penetration Pipes** (DN15×40, DN15×43, DN15×45)
- **Others**: Plastic Pipe, Meter Connector, Plug, Reducing Internal Thread

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Input Image                          │
│                    (2560×1440 JPEG)                       │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 1: FastSAM Segmentation + GridRescue (Otsu)       │
│  ─────────────────────────────────────────               │
│  • SAM-based instance segmentation (576×1024)             │
│  • Grid-based missed-detection rescue                    │
│  • IoU dedup + area gating (>50% image area = reject)    │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: HSV Physical Filter                            │
│  ────────────────────────────                            │
│  • Color / brightness / saturation gating                │
│  • Material inference: galvanized(light) / steel(dark)   │
│  • Pass rate: 73-100%                                    │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: CNN KNN Classification (MobileNetV2)           │
│  ────────────────────────────────────────────            │
│  • 1280-dim feature extraction                           │
│  • KNN (k=3, weighted) against gallery database          │
│  • Returns: broad category + material + confidence       │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4: DN Area Lookup                                 │
│  ───────────────────────                                 │
│  • Pixel-area → physical diameter mapping                │
│  • Calibration: 6.5062 px/mm @ 1280×720                  │
│  • Zero overlap: DN48/DN57/DN89                          │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 5: NCC Template Fine-match + SKU Override         │
│  ──────────────────────────────────────────────          │
│  • Within-category NCC template matching                  │
│  • 3-state: Hit(≥0.60) / Uncertain(≥0.45) / Miss(<0.45) │
│  • SKU override from learned corrections                 │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Output: Category + SKU + BBox                │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **8GB+ RAM** (16GB recommended for batch processing)
- **Windows** (primary platform, Linux/Mac untested)

### Installation

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/pipe-annotator.git
cd pipe-annotator

# 2. Create virtualenv
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download base models (see below)
```

### Model Downloads

Base models are NOT included in the repo (GitHub size limits). Download separately:

| Model | Size | Download | Required For |
|-------|------|----------|-------------|
| FastSAM-x.pt | 138 MB | [Ultralytics Assets](https://docs.ultralytics.com/models/fast-sam/) | Segmentation |
| yolo11n.pt | 5.4 MB | [Ultralytics Assets](https://docs.ultralytics.com/models/yolo11/) | YOLO detection (optional) |

Place both files in the project root directory.

### Run

```bash
python main.py
# or double-click run.bat
```

---

## 📂 Repository Structure

```
pipe-annotator/
├── src/                        # Core source code
│   ├── gui.py                  # Tkinter desktop UI + pipeline orchestration
│   ├── fastsam_segmenter.py    # FastSAM-based segmentation
│   ├── cnn_classifier.py       # MobileNetV2 feature extraction + KNN
│   ├── fitting_matcher.py      # NCC template matching
│   ├── camera.py               # Camera capture + Otsu segmentation
│   ├── yolo_exporter.py        # YOLO training data export
│   ├── yolo_detector.py        # YOLO detection integration
│   ├── detector.py             # Base detector interface
│   ├── database.py             # SQLite database operations
│   ├── corrections_db.py       # Correction learning database
│   ├── dn_lookup.py            # DN diameter lookup table
│   ├── material_classifier.py  # Material type classification
│   ├── feature_analysis.py     # Feature extraction utilities
│   ├── auto_train_yolo.py      # Automatic YOLO training loop
│   ├── session.py              # Session management
│   ├── form.py                 # Form UI components
│   ├── pipe_api.py             # Flask REST API
│   └── ...
├── main.py                     # Entry point
├── config.yaml                 # Configuration
├── requirements.txt            # Python dependencies
├── PIPELINE.md                 # Full pipeline documentation
├── run.bat                     # Windows launcher
├── setup.bat                   # First-time setup
└── demo/                       # Demo gallery (tiny subset)
```

---

## 🔄 Open Core Model

PipeAnnotator follows an **Open Core** model:

| What | License | 
|------|---------|
| Source code (src/) | **AGPL v3** — free to use, modify, distribute |
| Gallery database (59K ROI, 38 categories) | **Proprietary** — commercial license required |
| Trained YOLO model (best.pt) | **Proprietary** — commercial license required |
| Training data | **Proprietary** — not included |

**The demo gallery** (`demo/`) contains a tiny subset (~100 ROIs, 10 categories) sufficient for evaluation and development. For production use with 38 categories and full accuracy, a commercial license is required.

### Why AGPL v3?

AGPL ensures that anyone who modifies and deploys PipeAnnotator (including as a network service) must release their modifications. Companies that cannot comply with AGPL can purchase a commercial license.

### Commercial License

For commercial licensing inquiries (full gallery + trained models + support), contact the maintainer.

---

## 🎯 Use Cases

- **Quality Inspection**: Verify pipe fitting specifications against shipment manifests
- **Inventory Management**: Batch-scan warehouse stock and generate item lists
- **Construction Supply**: On-site fitting identification and counting
- **Training Data Generation**: Export YOLO-format segment annotations for custom model training

---

## 🧪 Technical Stack

| Component | Technology |
|-----------|-----------|
| Segmentation | FastSAM (Ultralytics) |
| Feature Extraction | MobileNetV2 (TorchVision) |
| Classification | KNN (k=3, cosine distance) |
| Template Matching | NCC (OpenCV) |
| GUI | Tkinter |
| Database | SQLite |
| API | Flask |
| ML Framework | PyTorch + Ultralytics |

---

## 📝 License

- **Source Code**: [GNU Affero General Public License v3.0](LICENSE)
- **Gallery & Models**: Proprietary — contact for commercial licensing

Copyright (C) 2026 Adam

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Areas where help is especially needed:

- Steel fitting detection improvements (low-contrast scenarios)
- Cross-platform support (macOS/Linux)
- GPU inference optimization
- Test coverage

---

## ⚠️ Disclaimer

This tool is designed for industrial pipe fitting recognition. Accuracy depends on image quality, lighting conditions, and gallery coverage. Always verify critical measurements manually. The authors assume no liability for misidentification.
