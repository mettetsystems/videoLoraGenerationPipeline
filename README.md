# videoLoraGenerationPipeline
Pipeline to Train Video LoRas
# WAN 2.1 LoRA Data Preparation Pipeline

> **Goal:** Prepare high-quality video scene clips for WAN 2.1 or LTX Video LoRA training.  
> This hybrid pipeline supports DVD ripping, automatic scene detection, scene splitting, and manual review before upscaling and captioning.

---

## 🚀 Overview

**wan21-lora-dataprep** is a modular data preparation toolkit for building custom video training datasets.  
It runs on **Windows 11** and **Fedora Linux (WSL)** and supports both **standalone scripts** and a **unified Typer CLI**.

**Pipeline stages:**

| Step | Description | Tools Used |
|------|--------------|-------------|
| 1️⃣ Rip | Extract videos from DVD/ISO to `.mkv` | MakeMKV |
| 2️⃣ Detect Scenes | Timestamp each scene | PySceneDetect |
| 3️⃣ Split Scenes | Split into clips using timestamps | MKVToolNix / FFmpeg |
| 4️⃣ Review | Stage for human review (keep/reject) | Custom script |

After review, the **`keep/`** folder is used for GPU upscaling and LoRA dataset creation (Phase 2).

---

## 🧰 Requirements

- Python ≥ 3.10  
- [MakeMKV](https://www.makemkv.com/)  
- [MKVToolNix](https://mkvtoolnix.download/)  
- [FFmpeg](https://ffmpeg.org/) (with NVENC for GPU systems)  
- [PySceneDetect](https://pyscenedetect.readthedocs.io/en/latest/)  
- Optional: [Prefect](https://www.prefect.io/) or [n8n](https://n8n.io/) for automation

---

## ⚙️ Environment Setup

### Windows (PowerShell)

```powershell
# clone repo
git clone https://github.com/<your-org>/<repo>.git
cd videoLoraGenerationPipeline

# create and activate venv
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# install in editable mode
pip install -e .
