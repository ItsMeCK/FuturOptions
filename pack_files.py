import zipfile
import os

def pack_project():
    output_filename = "deploy_package.zip"
    
    # Files to include (Allowlist approach is safer)
    files_to_include = [
        "live_brain.py",
        "trade_manager.py",
        "setup_gcp.sh",
        "requirements.txt",
        "notification_scheduler.py"
    ]
    
    # Directories to include (Recursive)
    dirs_to_include = [
        "notifications",
        "ai_option_brain"
        # "daily_data" # Skipped to reduce size
    ]

    # Models (Pickles)
    model_files = [f for f in os.listdir('.') if f.endswith('.pkl')]

    print(f"📦 Packing files into {output_filename}...")
    
    with zipfile.ZipFile(output_filename, 'w') as zipf:
        # Add root files
        for f in files_to_include:
            if os.path.exists(f):
                zipf.write(f)
                print(f"  + {f}")
        
        # Add Models
        for m in model_files:
            zipf.write(m)
            print(f"  + {m}")

        # Add Directories
        for d in dirs_to_include:
            for root, _, files in os.walk(d):
                if "__pycache__" in root: continue
                # Skip Data/Results/Logs Folders
                if "data" in root or "results" in root or "logs" in root: continue 
                
                for file in files:
                    if file == ".DS_Store": continue
                    if file.endswith(".pyc"): continue
                    if file.endswith(".csv"): continue # Exclude CSVs
                    if file.endswith("_rf_vol.pkl"): continue # Exclude unused RF models
                    if file.endswith(".log"): continue # Exclude logs
                    
                    file_path = os.path.join(root, file)
                    zipf.write(file_path)
                    print(f"  + {file_path}")
                    
    print(f"\n✅ Created {output_filename} successfully.")
    print("👉 Upload this file to your GCP Instance.")

if __name__ == "__main__":
    pack_project()
