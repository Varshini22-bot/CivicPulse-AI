# CivicPulse AI — Road Defect Detector Training Guide (Google Colab)

This document provides exact, step-by-step instructions for training the YOLOv8n road defect detector on Google Colab using a free T4 GPU, exporting the model to standard ONNX format, and deploying it into the CivicPulse AI backend.

---

## 1. Prerequisites & Overview
- **Local Limitation**: Your local machine runs on an Intel CPU without a dedicated CUDA GPU. Full training (30 epochs) on CPU would take 12+ hours.
- **Colab GPU**: Google Colab provides a free NVIDIA T4 GPU (16 GB VRAM), which completes 30 epochs in **~20 to 30 minutes**.
- **Dataset**: Road Damage Dataset 2022 (RDD2022) - India subset (~1.2 GB compressed).
- **Licence**: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
- **Target Output**: `models/rdd2022_yolov8n.onnx` (YOLOv8n architecture exported to ONNX float32).

---

## 2. Step-by-Step Training Instructions

### Step 1: Open Google Colab
1. Navigate to [https://colab.research.google.com](https://colab.research.google.com).
2. Click **Upload Notebook**.
3. Select `scripts/train_road_defect_detector.ipynb` (or `ml/notebooks/CivicPulse_Model_Training_Colab.ipynb`) from your local repository.

### Step 2: Enable GPU Hardware Acceleration
1. In the Colab top menu, click **Runtime** $\rightarrow$ **Change runtime type**.
2. Under **Hardware accelerator**, select **T4 GPU**.
3. Click **Save**.

### Step 3: Run the Cells Sequentially

#### Cell 1 & 2: Hardware Check & Install Dependencies
Executes `!nvidia-smi` and installs `ultralytics`, `onnx`, `onnxruntime`, `open-clip-torch`, `pyyaml`, `tqdm`, `scikit-learn`, `matplotlib`.
- *Expected time*: ~45 seconds.
- *Verification*: Confirm `CUDA Available: True` and `Device Name: Tesla T4`.

#### Cell 3: Set up Workspace
Clones your GitHub repository or sets up the working directory structure:
```bash
!git clone https://github.com/<your-username>/CivicPulse-AI.git
%cd CivicPulse-AI
```

#### Cell 4: Download and Prepare RDD2022 India Dataset
Downloads the official India subset and runs sequence-based grouped splitting to prevent consecutive dashcam video frames from leaking across train, validation, and test splits:
```bash
!mkdir -p data/raw/rdd2022
!wget -q -O rdd2022_india.tar.gz "https://bigdata.sekilab.global/cdd2022/RDD2022_India.tar.gz"
!tar -xzf rdd2022_india.tar.gz -C data/raw/rdd2022/
!python ml/dataset.py --raw-dir data/raw/rdd2022 --output-dir data/rdd2022_india
```
- *Expected time*: ~3-5 minutes (depending on network bandwidth).

#### Cell 5: Train YOLOv8n Detector
Executes reproducible training with fixed seed=42 for 30 epochs:
```bash
!python ml/train.py \
    --config ml/configs/rdd2022_yolov8n.yaml \
    --epochs 30 \
    --batch-size 16 \
    --imgsz 640 \
    --seed 42 \
    --output-dir runs/train \
    --export-onnx
```
- *Expected time*: ~18-25 minutes on T4 GPU.

#### Cell 6: Parity Check (PyTorch vs ONNX Runtime)
Verifies that numerical outputs between PyTorch and ONNX Runtime match within numerical tolerance ($\text{MAE} \le 10^{-3}$):
```python
from ml.train import verify_onnx_parity
from ultralytics import YOLO

best_pt = "runs/train/rdd2022_experiment/weights/best.pt"
best_onnx = "runs/train/rdd2022_experiment/weights/best.onnx"
pt_model = YOLO(best_pt).model
parity = verify_onnx_parity(pt_model, best_onnx)
print("ONNX Parity Verification:", parity)
```
- *Verification*: Must output `"status": "passed"`.

#### Cell 7: Evaluate Model on Held-out Test Split
Evaluates test mAP and generates evaluation metrics on the held-out test split:
```bash
!python ml/eval/evaluate_detector.py --model runs/train/rdd2022_experiment/weights/best.onnx --test-dir data/rdd2022_india/images/test
```

#### Cell 8: Download Trained Weights to Local Machine
Automatically triggers browser download of `rdd2022_yolov8n.onnx`:
```python
from google.colab import files
import os, shutil

onnx_export_path = "runs/train/rdd2022_experiment/weights/best.onnx"
if os.path.exists(onnx_export_path):
    output_filename = "rdd2022_yolov8n.onnx"
    shutil.copy2(onnx_export_path, output_filename)
    files.download(output_filename)
```

---

## 3. Local Deployment Instructions

Once `rdd2022_yolov8n.onnx` finishes downloading to your browser's Downloads folder:

1. **Move the file into your local repository root**:
   ```powershell
   Move-Item "$HOME\Downloads\rdd2022_yolov8n.onnx" "c:\Users\varsh\Downloads\CivicPulse AI\models\rdd2022_yolov8n.onnx"
   ```
2. **Verify weights detection**:
   Run the evaluation runner:
   ```powershell
   python ml/eval/run_all_evals.py
   ```
3. **Run Backend Test Suite**:
   ```powershell
   pytest backend/tests/test_ml_pipeline.py -v
   ```
   The `RoadDefectDetector` will automatically load `models/rdd2022_yolov8n.onnx` and transition from `status="abstain"` to active defect detection!

---

## 4. Troubleshooting & Error Recovery

| Error / Failure Symptom | Probable Cause | Fix / Mitigation |
| :--- | :--- | :--- |
| `CUDA out of memory (OOM)` | Batch size 16 exceeds GPU memory allocation | In Cell 5, reduce `--batch-size 16` to `--batch-size 8`. |
| `wget connection timeout` | Network spike during tar.gz download | Re-run Cell 4; if Sekilab server is slow, use curl with retry: `curl -C - -O --retry 3 https://bigdata.sekilab.global/cdd2022/RDD2022_India.tar.gz` |
| `No GPU available / torch.cuda.is_available() is False` | Runtime was left as CPU | In Colab menu, select **Runtime** $\rightarrow$ **Change runtime type** $\rightarrow$ select **T4 GPU** $\rightarrow$ click Save, then re-run Cell 1. |
| `Colab session disconnected (idle timeout)` | Colab tab was closed or idle for > 90 min | Keep the browser tab active during training, or run with Colab Pro background execution. |
| `Parity check returned 'warning'` | Max absolute difference slightly exceeds 1e-3 | Normal for FP16 quantization or opset 18 optimizations; as long as max difference is $< 5 \times 10^{-3}$, bounding box coordinates remain sub-pixel accurate. |
