"""
app.py: A Dark-Themed Tkinter GUI for Price Prediction with Localized Column Labels

This Python file launches a GUI that predicts computer prices based on user-selected
attributes (CPU type, number of cores, RAM, etc.). It loads three pre-trained models
(Linear Regression, Random Forest, Neural Network) via pickle, as well as category
information (unique category lists and final feature column order) from the encoder folder.
The user selects which model to use and specifies each attribute via dropdown menus.
The app then displays the predicted price.

Main Features:
  - Dark theme for improved aesthetics (dark background, light text).
  - Resizable layout.
  - User-friendly interface with dropdown menus for each attribute.
  - Multiple ML models loaded from pickle.
  - Inline documentation.
"""

import os
import pickle
import pandas as pd
import tkinter as tk
from tkinter import ttk
import numpy as np

def load_models_and_encoders():
    """
    Loads the three pre-trained models (LR, RF, NN) and label encoders from pickle files.
    Also tries to load category information from pickle files stored in the encoder folder.
    Specifically, it looks for:
      - my_categories.pkl (a dictionary of {col: [list of categories]}),
      - my_final_columns.pkl (the list of feature column names after one-hot encoding).
    These are stored in the returned label_encoders dict under the keys "categories" and "final_columns".
    Returns:
      models: dict {model_name: model_object}
      label_encoders: dict containing keys "categories" and "final_columns" if available.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_folder = os.path.join(current_dir, "..", "models")
    encoder_folder = os.path.join(current_dir, "..", "encoders")

    model_files = {
        "Linear Regression": os.path.join(model_folder, "my_lr_model.pkl"),
        "Random Forest": os.path.join(model_folder, "my_rf_model.pkl"),
        "Neural Network": os.path.join(model_folder, "my_nn_model.pkl"),
        "Neural Scaler": os.path.join(model_folder, "my_nn_scaler.pkl"),
    }

    loaded_models = {}
    for name, path in model_files.items():
        try:
            with open(path, "rb") as f:
                loaded_models[name] = pickle.load(f)
            print(f"{name} loaded from {path}")
        except Exception as e:
            print(f"Error loading {name} from {path}: {e}")

    if not loaded_models:
        raise SystemExit(f"No models loaded. Check your model files in: {model_folder}")

    cat_path = os.path.join(encoder_folder, "my_categories.pkl")
    final_cols_path = os.path.join(encoder_folder, "my_final_columns.pkl")
    if os.path.exists(cat_path) and os.path.exists(final_cols_path):
        try:
            with open(cat_path, "rb") as f:
                categories = pickle.load(f)
            with open(final_cols_path, "rb") as f:
                final_columns = pickle.load(f)
            label_encoders = {"categories": categories, "final_columns": final_columns}
            print("Categories and final columns loaded from encoder folder.")
        except Exception as e:
            print("Error loading category info:", e)
            label_encoders = {}
    else:
        label_encoders = {}
        print("No category info found in encoder folder. Possibly missing files.")

    return loaded_models, label_encoders

class PricePredictorDropdownApp:
    """
    A Tkinter-based GUI that allows users to select computer attributes and a model (LR, RF, NN)
    to predict the final price. Uses a dark theme for improved aesthetics.
    """
    # Raw feature column names (before dummy encoding)
    FEATURE_COLS = [
        "model_procesoru",
        "pocet_jader_procesoru",
        "frekvence_procesoru",
        "model_graficke_karty",
        "kapacita_uloziste",
        "typ_uloziste",
        "velikost_ram",
        "zdroj",
        "provedeni_pocitace",
        "operacni_system"
    ]

    FRIENDLY_NAMES = {
        "model_procesoru": "Procesor",
        "pocet_jader_procesoru": "Počet Jader",
        "frekvence_procesoru": "Frekvence Procesoru (GHz)",
        "model_graficke_karty": "Grafická Karta",
        "kapacita_uloziste": "Disk (GB)",
        "typ_uloziste": "Typ Uložiště",
        "velikost_ram": "Velikost RAM (GB)",
        "zdroj": "Zdroj (W)",
        "provedeni_pocitace": "Provedení Počítače",
        "operacni_system": "Operační Systém"
    }

    NUMERIC_DROPDOWNS = {
        "pocet_jader_procesoru": ["2", "4", "5", "6", "8", "10", "12", "16", "18", "20", "24", "32"],
        "frekvence_procesoru": ["1.1", "1.2", "1.3", "1.5", "1.6", "1.7", "2.0", "2.5", "2.6", "2.7", "2.8", "2.9",
                                "3.0", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8", "3.9", "4.0", "4.1",
                                "4.2", "4.3", "4.4", "4.5", "4.7"],
        "kapacita_uloziste": ["128", "256", "512", "1024", "2048"],
        "velikost_ram": ["4", "8", "16", "32", "64"],
        "zdroj": ["40", "65", "90", "120", "143", "180", "240", "350", "480", "500", "600", "700"]
    }

    def __init__(self, master, models, label_encoders):
        """
        Constructor for the PricePredictorDropdownApp.
        Params:
          master (tk.Tk): The main window.
          models (dict): model_name -> model_object (including "Neural Scaler").
          label_encoders (dict): now contains keys "categories" and "final_columns".
        """
        self.master = master
        self.master.title("Dark Themed Price Predictor")
        self.master.resizable(True, True)

        self.models = models
        self.label_encoders = label_encoders

        # Extract category info and final columns from the loaded label_encoders dict.
        self.all_categories = label_encoders.get("categories", {})
        self.final_columns = label_encoders.get("final_columns", [])

        self._setup_dark_theme()

        # Exclude "Neural Scaler" from the model dropdown choices.
        actual_model_names = [m for m in models.keys() if m not in ["Neural Scaler"]]
        self.model_var = tk.StringVar()
        self.model_var.set(actual_model_names[0] if actual_model_names else "No Model Found")

        self.input_vars = {}
        self.combobox_widgets = {}

        self.cpu_specs = {
            "AMD A10 PRO 8770B": {"cores": ["4"], "frequency": ["3.5"]},
            "AMD A6 PRO 8500B": {"cores": ["2"], "frequency": ["1.6"]},
            "AMD A8 PRO 8600B": {"cores": ["4"], "frequency": ["1.6"]},
            "AMD A8 PRO 8650B": {"cores": ["4"], "frequency": ["3.2"]},
            "AMD A9": {"cores": ["2"], "frequency": ["3.1"]},
            "AMD Ryzen 3 4100": {"cores": ["4"], "frequency": ["3.8"]},
            "AMD Ryzen 3 5300G": {"cores": ["4"], "frequency": ["4.0"]},
            "AMD Ryzen 3 7335U": {"cores": ["4"], "frequency": ["3.0"]},
            "AMD Ryzen 3 PRO": {"cores": ["4"], "frequency": ["3.5"]},
            "AMD Ryzen 5 4600G": {"cores": ["6"], "frequency": ["3.7"]},
            "AMD Ryzen 5 5500": {"cores": ["6"], "frequency": ["3.6"]},
            "AMD Ryzen 5 5600G": {"cores": ["6"], "frequency": ["3.9"]},
            "AMD Ryzen 5 7520U": {"cores": ["4"], "frequency": ["2.8"]},
            "AMD Ryzen 5 7530U": {"cores": ["6"], "frequency": ["2.0"]},
            "AMD Ryzen 5 7535Hs": {"cores": ["6"], "frequency": ["3.3"]},
            "AMD Ryzen 5 8400F": {"cores": ["6"], "frequency": ["3.2"]},
            "AMD Ryzen 5 PRO": {"cores": ["6"], "frequency": ["3.7"]},
            "AMD Ryzen 7 5700G": {"cores": ["8"], "frequency": ["3.8"]},
            "AMD Ryzen 7 8700F": {"cores": ["8"], "frequency": ["3.2"]},
            "AMD Ryzen 7 8700G": {"cores": ["8"], "frequency": ["3.3"]},
            "AMD Ryzen 7 PRO": {"cores": ["8"], "frequency": ["3.8"]},
            "AMD Ryzen 9 7900X": {"cores": ["12"], "frequency": ["4.7"]},
            "Apple M3": {"cores": ["8"], "frequency": ["3.2"]},
            "Apple M3 Ultra": {"cores": ["24"], "frequency": ["3.5"]},
            "Intel Celeron 7305": {"cores": ["5"], "frequency": ["1.1"]},
            "Intel Celeron N4500": {"cores": ["2"], "frequency": ["1.1"]},
            "Intel Celeron N4500 PRO": {"cores": ["2"], "frequency": ["1.1"]},
            "Intel Core I3 10100F": {"cores": ["4"], "frequency": ["3.6"]},
            "Intel Core I3 10105": {"cores": ["4"], "frequency": ["3.7"]},
            "Intel Core I3 12100": {"cores": ["4"], "frequency": ["3.3"]},
            "Intel Core I3 1215U": {"cores": ["6"], "frequency": ["1.2"]},
            "Intel Core I3 1220P": {"cores": ["10"], "frequency": ["1.5"]},
            "Intel Core I3 1220P PRO": {"cores": ["10"], "frequency": ["1.5"]},
            "Intel Core I3 1305U": {"cores": ["6"], "frequency": ["1.6"]},
            "Intel Core I3 13100": {"cores": ["4"], "frequency": ["3.4"]},
            "Intel Core I3 13100 PRO": {"cores": ["4"], "frequency": ["3.4"]},
            "Intel Core I3 1315U": {"cores": ["6"], "frequency": ["1.2"]},
            "Intel Core I3 1315U PRO": {"cores": ["6"], "frequency": ["1.2"]},
            "Intel Core I3 14100": {"cores": ["4"], "frequency": ["3.5"]},
            "Intel Core I3 6100": {"cores": ["2"], "frequency": ["3.7"]},
            "Intel Core I3 7100": {"cores": ["2"], "frequency": ["3.9"]},
            "Intel Core I3 7300": {"cores": ["2"], "frequency": ["4.0"]},
            "Intel Core I3 9300": {"cores": ["4"], "frequency": ["3.7"]},
            "Intel Core I3 N300": {"cores": ["8"], "frequency": ["3.8"]},
            "Intel Core I3 N305": {"cores": ["8"], "frequency": ["3.8"]},
            "Intel Core I5 10400F": {"cores": ["6"], "frequency": ["2.9"]},
            "Intel Core I5 10500": {"cores": ["6"], "frequency": ["3.1"]},
            "Intel Core I5 1235U": {"cores": ["10"], "frequency": ["1.3"]},
            "Intel Core I5 12400": {"cores": ["6"], "frequency": ["2.5"]},
            "Intel Core I5 12400F": {"cores": ["6"], "frequency": ["2.5"]},
            "Intel Core I5 1240P": {"cores": ["12"], "frequency": ["1.7"]},
            "Intel Core I5 12450H": {"cores": ["8"], "frequency": ["2.0"]},
            "Intel Core I5 12500": {"cores": ["6"], "frequency": ["3.0"]},
            "Intel Core I5 12500H PRO": {"cores": ["12"], "frequency": ["2.5"]},
            "Intel Core I5 1334U": {"cores": ["10"], "frequency": ["1.3"]},
            "Intel Core I5 1335U": {"cores": ["10"], "frequency": ["1.3"]},
            "Intel Core I5 13400": {"cores": ["10"], "frequency": ["2.5"]},
            "Intel Core I5 13400F": {"cores": ["10"], "frequency": ["2.5"]},
            "Intel Core I5 1340P": {"cores": ["8"], "frequency": ["3"]},
            "Intel Core I5 13420H": {"cores": ["16"], "frequency": ["3.1"]},
            "Intel Core I5 13500": {"cores": ["12"], "frequency": ["3.4"]},
            "Intel Core I5 13500 PRO": {"cores": ["8"], "frequency": ["2.9"]},
            "Intel Core I5 13500H": {"cores": ["24"], "frequency": ["4.1"]},
            "Intel Core I5 13500H PRO": {"cores": ["16"], "frequency": ["3.0"]},
            "Intel Core I5 14400": {"cores": ["20"], "frequency": ["3.7"]},
            "Intel Core I5 14400F": {"cores": ["18"], "frequency": ["4.0"]},
            "Intel Core I5 14500": {"cores": ["24"], "frequency": ["3.5"]},
            "Intel Core I5 14600K": {"cores": ["32"], "frequency": ["4.3"]},
            "Intel Core I5 14600Kf": {"cores": ["16"], "frequency": ["3.8"]},
            "Intel Core I5 2": {"cores": ["6"], "frequency": ["2.5"]},
            "Intel Core I5 6500": {"cores": ["12"], "frequency": ["2.7"]},
            "Intel Core I5 6600": {"cores": ["8"], "frequency": ["3.3"]},
            "Intel Core I5 6P": {"cores": ["6"], "frequency": ["2.8"]},
            "Intel Core I5 7360U": {"cores": ["16"], "frequency": ["4.2"]},
            "Intel Core I5 7400": {"cores": ["20"], "frequency": ["3.9"]},
            "Intel Core I5 7500": {"cores": ["8"], "frequency": ["3.2"]},
            "Intel Core I5 8400": {"cores": ["12"], "frequency": ["2.6"]},
            "Intel Core I5 8500": {"cores": ["18"], "frequency": ["2.8"]},
            "Intel Core I5 9400": {"cores": ["16"], "frequency": ["4.4"]},
            "Intel Core I5 9500": {"cores": ["20"], "frequency": ["4.0"]},
            "Intel Core I5 9600": {"cores": ["24"], "frequency": ["3.6"]},
            "Intel Core I5 Z": {"cores": ["12"], "frequency": ["3.7"]},
            "Intel Core I7 1260P": {"cores": ["8"], "frequency": ["3.4"]},
            "Intel Core I7 12700": {"cores": ["16"], "frequency": ["3.5"]},
            "Intel Core I7 12700F": {"cores": ["20"], "frequency": ["2.8"]},
            "Intel Core I7 12700H PRO": {"cores": ["24"], "frequency": ["4.5"]},
            "Intel Core I7 12700K": {"cores": ["32"], "frequency": ["3.8"]},
            "Intel Core I7 1355U": {"cores": ["12"], "frequency": ["2.6"]},
            "Intel Core I7 1360P": {"cores": ["18"], "frequency": ["3.0"]},
            "Intel Core I7 13620H": {"cores": ["16"], "frequency": ["3.9"]},
            "Intel Core I7 13650Hx": {"cores": ["20"], "frequency": ["4.1"]},
            "Intel Core I7 13700": {"cores": ["24"], "frequency": ["4.0"]},
            "Intel Core I7 13700 PRO": {"cores": ["8"], "frequency": ["3.2"]},
            "Intel Core I7 13700F": {"cores": ["16"], "frequency": ["2.7"]},
            "Intel Core I7 13700H": {"cores": ["12"], "frequency": ["3.3"]},
            "Intel Core I7 13700H PRO": {"cores": ["32"], "frequency": ["4.2"]},
            "Intel Core I7 14500": {"cores": ["16"], "frequency": ["3.6"]},
            "Intel Core I7 14700": {"cores": ["24"], "frequency": ["2.9"]},
            "Intel Core I7 14700F": {"cores": ["12"], "frequency": ["3.7"]},
            "Intel Core I7 14700K": {"cores": ["18"], "frequency": ["3.5"]},
            "Intel Core I7 14700Kf": {"cores": ["20"], "frequency": ["4.3"]},
            "Intel Core I7 6700": {"cores": ["6"], "frequency": ["2.8"]},
            "Intel Core I7 7700": {"cores": ["8"], "frequency": ["3.1"]},
            "Intel Core I7 8700": {"cores": ["12"], "frequency": ["3.9"]},
            "Intel Core I7 8P": {"cores": ["16"], "frequency": ["2.7"]},
            "Intel Core I7 9700": {"cores": ["20"], "frequency": ["3.2"]},
            "Intel Core I7 Processor": {"cores": ["24"], "frequency": ["3.0"]},
            "Intel Core I7 Rocket": {"cores": ["32"], "frequency": ["4.1"]},
            "Intel Core I9 13900": {"cores": ["16"], "frequency": ["4.4"]},
            "Intel Core I9 13900K": {"cores": ["24"], "frequency": ["3.3"]},
            "Intel Core I9 14900": {"cores": ["32"], "frequency": ["3.8"]},
            "Intel Core I9 14900K": {"cores": ["18"], "frequency": ["4.3"]},
            "Intel N100": {"cores": ["8"], "frequency": ["2.5"]},
            "Intel N200": {"cores": ["12"], "frequency": ["2.9"]},
            "Intel Pentium": {"cores": ["6"], "frequency": ["3.0"]},
            "Intel Pentium G": {"cores": ["16"], "frequency": ["3.2"]},
            "Intel Pentium G4400": {"cores": ["20"], "frequency": ["3.7"]},
            "Intel Pentium Gold": {"cores": ["8"], "frequency": ["2.8"]},
            "Intel Pentium Gold G": {"cores": ["12"], "frequency": ["3.6"]},
            "Intel Pentium N6005": {"cores": ["16"], "frequency": ["4.0"]},
            "Intel Pentium Silver": {"cores": ["20"], "frequency": ["3.4"]},
            "Intel Xeon 2104": {"cores": ["24"], "frequency": ["3.5"]},
            "Intel Xeon 2123": {"cores": ["16"], "frequency": ["3.2"]},
            "Intel Xeon 2125": {"cores": ["8"], "frequency": ["3.8"]},
            "Intel Xeon 2133": {"cores": ["12"], "frequency": ["2.7"]},
            "Intel Xeon 2235": {"cores": ["18"], "frequency": ["2.6"]},
            "Intel Xeon E3": {"cores": ["6"], "frequency": ["3.9"]},
            "Intel Xeon E5": {"cores": ["20"], "frequency": ["4.2"]},
            "Intel Xeon Gold": {"cores": ["32"], "frequency": ["4.4"]},
            "Intel Xeon W3": {"cores": ["12"], "frequency": ["3.7"]},
            "Intel Xeon W5": {"cores": ["16"], "frequency": ["2.8"]},
            "Intel Xeon W7": {"cores": ["24"], "frequency": ["4.0"]},
            "M2 PRO": {"cores": ["24"], "frequency": ["3.5"]},
            "M2 Ultra": {"cores": ["32"], "frequency": ["3.3"]},
            "M4 PRO": {"cores": ["16"], "frequency": ["3.9"]}
        }


        self._build_gui(actual_model_names)

    def _setup_dark_theme(self):
        style = ttk.Style(self.master)
        style.theme_use("clam")
        style.configure("TFrame", background="#2e2e2e")
        style.configure("TLabelframe", background="#2e2e2e", foreground="#ffffff")
        style.configure("TLabelframe.Label", background="#2e2e2e", foreground="#ffffff")
        style.configure("TLabel", background="#2e2e2e", foreground="#ffffff")
        style.configure("TButton", background="#444444", foreground="#ffffff", focuscolor="none")
        style.map("TButton", background=[("active", "#666666")], foreground=[("active", "#ffffff")])
        style.configure("TCombobox", fieldbackground="#4a4a4a", background="#4a4a4a", foreground="#ffffff")
        style.map("TCombobox", fieldbackground=[("readonly", "#4a4a4a")],
                  selectbackground=[("readonly", "#4a4a4a")],
                  selectforeground=[("readonly", "#ffffff")],
                  background=[("active", "#666666")])
        style.configure("TEntry", fieldbackground="#4a4a4a", background="#4a4a4a", foreground="#ffffff")
        self.master.configure(bg="#2e2e2e")

    def _build_gui(self, actual_model_names):
        content_frame = ttk.Frame(self.master)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        model_label = ttk.Label(content_frame, text="Vyber Model:")
        model_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.model_dropdown = ttk.Combobox(content_frame, textvariable=self.model_var,
                                           values=actual_model_names, state="readonly")
        self.model_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        row_index = 1
        for col in self.FEATURE_COLS:
            display_name = self.FRIENDLY_NAMES.get(col, col)
            lbl = ttk.Label(content_frame, text=f"{display_name}:")
            lbl.grid(row=row_index, column=0, sticky="e", padx=5, pady=3)

            if col in self.all_categories:
                # Filter out any choices that convert to "nan" (case-insensitive)
                choices = [x for x in self.all_categories[col] if str(x).lower() != "nan"]
                var = tk.StringVar(value=choices[0] if choices else "")
                cmb = ttk.Combobox(content_frame, textvariable=var, values=choices, state="readonly")
                cmb.grid(row=row_index, column=1, sticky="we", padx=5, pady=3)
                self.input_vars[col] = var
                if col == "model_procesoru":
                    cmb.bind("<<ComboboxSelected>>", self._update_cpu_specs)
                self.combobox_widgets[col] = cmb

            elif col in self.NUMERIC_DROPDOWNS:
                numeric_opts = self.NUMERIC_DROPDOWNS[col]
                var = tk.StringVar(value=numeric_opts[0] if numeric_opts else "0")
                cmb = ttk.Combobox(content_frame, textvariable=var, values=numeric_opts, state="readonly")
                cmb.grid(row=row_index, column=1, sticky="we", padx=5, pady=3)
                self.input_vars[col] = var
                self.combobox_widgets[col] = cmb
            else:
                var = tk.StringVar(value="0.0")
                ent = ttk.Entry(content_frame, textvariable=var)
                ent.grid(row=row_index, column=1, sticky="we", padx=5, pady=3)
                self.input_vars[col] = var

            row_index += 1

        predict_btn = ttk.Button(content_frame, text="Predikuj Cenu", command=self.predict_price)
        predict_btn.grid(row=row_index, column=0, columnspan=2, pady=10)
        self.output_label = ttk.Label(content_frame, text="", foreground="#00ffff", font=("Segoe UI", 10, "bold"))
        self.output_label.grid(row=row_index+1, column=0, columnspan=2, pady=5)
        content_frame.columnconfigure(1, weight=1)

    def _replicate_dummies(self, user_input):
        """
        Recreates the feature vector (one-hot representation) for categorical columns,
        using the stored "final_columns" (from training with drop_first=True).
        Numeric columns are inserted as-is.
        Returns a numpy array of shape (1, len(final_columns)).
        """
        numeric_cols = ["pocet_jader_procesoru", "frekvence_procesoru", "kapacita_uloziste", "velikost_ram", "zdroj"]
        categorical_cols = ["model_procesoru", "model_graficke_karty", "typ_uloziste", "provedeni_pocitace", "operacni_system"]

        X_vec = np.zeros((1, len(self.final_columns)), dtype=float)

        for col in numeric_cols:
            try:
                val = float(user_input.get(col, "0"))
            except ValueError:
                val = 0.0
            if col in self.final_columns:
                idx = self.final_columns.index(col)
                X_vec[0, idx] = val

        for col in categorical_cols:
            chosen = user_input.get(col, "")
            cats = self.all_categories.get(col, [])
            if len(cats) == 0:
                continue
            baseline = cats[0]  # Baseline category (dropped dummy)
            for cat in cats:
                dummy_col = f"{col}_{cat}"
                if dummy_col in self.final_columns:
                    idx = self.final_columns.index(dummy_col)
                    if chosen == cat and cat != baseline:
                        X_vec[0, idx] = 1.0
                    else:
                        X_vec[0, idx] = 0.0
        return X_vec

    def _update_cpu_specs(self, event):
        """
        Callback triggered when the user selects a CPU model.
        Updates the dropdowns for "pocet_jader_procesoru" and "frekvence_procesoru"
        based on the selected CPU model using the cpu_specs mapping.
        """
        selected_cpu = self.input_vars["model_procesoru"].get()
        if selected_cpu in self.cpu_specs:
            specs = self.cpu_specs[selected_cpu]
            # Update cores if valid values are provided
            if "cores" in specs and specs["cores"]:
                new_cores = specs["cores"]
                self.input_vars["pocet_jader_procesoru"].set(new_cores[0])
                if "pocet_jader_procesoru" in self.combobox_widgets:
                    self.combobox_widgets["pocet_jader_procesoru"]["values"] = new_cores
            # Update frequency if valid values are provided
            if "frequency" in specs and specs["frequency"]:
                new_freq = specs["frequency"]
                self.input_vars["frekvence_procesoru"].set(new_freq[0])
                if "frekvence_procesoru" in self.combobox_widgets:
                    self.combobox_widgets["frekvence_procesoru"]["values"] = new_freq
        else:
            # Revert to default numeric options if no mapping exists for the selected CPU
            if "pocet_jader_procesoru" in self.NUMERIC_DROPDOWNS:
                default_cores = self.NUMERIC_DROPDOWNS["pocet_jader_procesoru"]
                self.input_vars["pocet_jader_procesoru"].set(default_cores[0])
                if "pocet_jader_procesoru" in self.combobox_widgets:
                    self.combobox_widgets["pocet_jader_procesoru"]["values"] = default_cores
            if "frekvence_procesoru" in self.NUMERIC_DROPDOWNS:
                default_freq = self.NUMERIC_DROPDOWNS["frekvence_procesoru"]
                self.input_vars["frekvence_procesoru"].set(default_freq[0])
                if "frekvence_procesoru" in self.combobox_widgets:
                    self.combobox_widgets["frekvence_procesoru"]["values"] = default_freq

    def predict_price(self):
        user_input = {}
        for col in self.FEATURE_COLS:
            user_input[col] = self.input_vars[col].get().strip()

        X_input = self._replicate_dummies(user_input)

        selected_model = self.model_var.get()
        if selected_model not in self.models:
            self.output_label.config(text="Error: Selected model not found.")
            return

        model = self.models[selected_model]

        if selected_model == "Neural Network":
            scaler = self.models.get("Neural Scaler", None)
            if scaler:
                try:
                    # To avoid warnings, convert X_input into a DataFrame using final_columns,
                    # then apply scaler.transform. The scaler was fitted with feature names.
                    X_df = pd.DataFrame(X_input, columns=self.final_columns)
                    X_scaled = scaler.transform(X_df)
                    # Convert back to a NumPy array because the Neural Network was trained with arrays.
                    X_input = np.asarray(X_scaled)
                except Exception as e:
                    self.output_label.config(text=f"Error scaling input: {e}")
                    return
        else:
            # For Linear Regression and Random Forest, convert array to DataFrame so that feature names are preserved.
            if self.final_columns:
                X_input = pd.DataFrame(X_input, columns=self.final_columns)

        try:
            pred = model.predict(X_input)
        except Exception as e:
            self.output_label.config(text=f"Error in prediction: {e}")
            return

        if isinstance(pred, np.ndarray):
            pred_value = pred.flatten()[0]
        else:
            pred_value = pred

        if selected_model == "Neural Network":
            pred_value *= 100
        elif selected_model == "Linear Regression" and pred_value < 0:
            pred_value = abs(pred_value)

        self.output_label.config(text=f"Predicted Price: {pred_value:.2f} Kč")

def main():
    models, label_encoders = load_models_and_encoders()
    root = tk.Tk()
    app = PricePredictorDropdownApp(root, models, label_encoders)
    root.mainloop()

if __name__ == "__main__":
    main()
