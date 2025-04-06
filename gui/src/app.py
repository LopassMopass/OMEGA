"""
app.py: A Dark-Themed Tkinter GUI for Price Prediction with Localized Column Labels

This Python file launches a GUI that predicts computer prices based on user-selected
attributes (CPU type, number of cores, RAM, etc.). It loads three pre-trained models
(Linear Regression, Random Forest, Neural Network) via pickle, as well as label encoders
(if available). The user selects which model to use and specifies each attribute via
dropdown menus. The app then displays the predicted price.

New Feature:
  - Friendly / localized display names for columns (Procesor, Počet Jader, Frekvence, etc.).

Main Features:
  - Dark theme for improved aesthetics (dark background, light text).
  - Resizable layout (window can be resized horizontally and vertically).
  - Simple, user-friendly interface with dropdown menus for each attribute.
  - Multiple ML models (LR, RF, NN) loaded from pickle, no training or .json reading here.
  - Inline documentation to clarify code structure and purpose.
"""

import os
import pickle
import tkinter as tk
from tkinter import ttk
import numpy as np

def load_models_and_encoders():
    """
    Loads the three pre-trained models (LR, RF, NN) and label encoders from pickle files.
    Returns:
      models: dict {model_name: model_object}
      label_encoders: dict {column_name: encoder_object}
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_folder = os.path.join(current_dir, "..", "models")
    encoder_folder = os.path.join(current_dir, "..", "encoders")

    model_files = {
        "Linear Regression": os.path.join(model_folder, "my_lr_model.pkl"),
        "Random Forest": os.path.join(model_folder, "my_rf_model.pkl"),
        "Neural Network": os.path.join(model_folder, "my_nn_model.pkl")
    }

    # Load models
    loaded_models = {}
    for name, path in model_files.items():
        try:
            with open(path, "rb") as f:
                loaded_models[name] = pickle.load(f)
            print(f"{name} loaded from {path}")
        except Exception as e:
            print(f"Error loading {name} from {path}: {e}")

    # If no models are loaded, stop the program
    if not loaded_models:
        raise SystemExit(f"No models loaded. Check your model files in: {model_folder}")

    # Load label encoders if present
    label_encoders_path = os.path.join(encoder_folder, "my_label_encoders.pkl")
    if os.path.exists(label_encoders_path):
        with open(label_encoders_path, "rb") as f:
            label_encoders = pickle.load(f)
        print("Label encoders loaded.")
    else:
        label_encoders = {}
        print("No label encoders found. Possibly all attributes are numeric or missing encoders.")

    return loaded_models, label_encoders

class PricePredictorDropdownApp:
    """
    A Tkinter-based GUI that allows users to select computer attributes and a model (LR, RF, NN)
    to predict the final price. Uses a dark theme for improved aesthetics.
    """

    # Internal column names
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

    # Friendly display names for the above columns
    FRIENDLY_NAMES = {
        "model_procesoru": "Procesor",
        "pocet_jader_procesoru": "Počet Jader",
        "frekvence_procesoru": "Frekvence Procesoru",
        "model_graficke_karty": "Grafická Karta",
        "kapacita_uloziste": "Kapacita Uložiště",
        "typ_uloziste": "Typ Uložiště",
        "velikost_ram": "Velikost RAM",
        "zdroj": "Zdroj",
        "provedeni_pocitace": "Provedení Počítače",
        "operacni_system": "Operační Systém"
    }

    # Numeric dropdowns for certain columns
    NUMERIC_DROPDOWNS = {
        "pocet_jader_procesoru": ["2", "4", "6", "8", "10", "12", "14", "16", "18", "20"],
        "frekvence_procesoru": ["2.0", "2.5", "3.0", "3.5", "4.0", "4.5", "5.0"],
        "kapacita_uloziste": ["128", "256", "512", "1024", "2048"],
        "velikost_ram": ["4", "8", "16", "32", "64"],
        "zdroj": ["40", "65", "90", "120", "143", "180", "240", "350", "480", "500", "600", "700"]
    }

    def __init__(self, master, models, label_encoders):
        """
        Constructor for the PricePredictorDropdownApp.
        Params:
          master (tk.Tk): The main window or root.
          models (dict): A dictionary of model_name -> model_object loaded from pickle.
          label_encoders (dict): A dictionary of col_name -> LabelEncoder object.
        """
        self.master = master
        self.master.title("Dark Themed Price Predictor")
        self.master.resizable(True, True)  # Allow user to resize in both directions.

        # Save references
        self.models = models
        self.label_encoders = label_encoders

        # Setup style for a dark theme
        self._setup_dark_theme()

        # Prepare user input variables
        self.model_var = tk.StringVar()
        # Default to the first model if any exist
        model_keys = list(models.keys())
        self.model_var.set(model_keys[0] if model_keys else "No Model Found")

        # Dictionary to store user inputs for each feature
        self.input_vars = {}

        # Build the interface
        self._build_gui()

    def _setup_dark_theme(self):
        """
        Configures a dark theme for all widgets using ttk.Style.
        """
        style = ttk.Style(self.master)
        # Switch to a theme that allows custom styling
        style.theme_use("clam")

        # General background
        style.configure("TFrame", background="#2e2e2e")
        style.configure("TLabelframe", background="#2e2e2e", foreground="#ffffff")
        style.configure("TLabelframe.Label", background="#2e2e2e", foreground="#ffffff")
        style.configure("TLabel", background="#2e2e2e", foreground="#ffffff")
        style.configure("TButton",
                        background="#444444",
                        foreground="#ffffff",
                        focuscolor="none")
        style.map("TButton",
                  background=[("active", "#666666")],
                  foreground=[("active", "#ffffff")])
        style.configure("TCombobox",
                        fieldbackground="#4a4a4a",
                        background="#4a4a4a",
                        foreground="#ffffff")
        # Make the combobox arrow button also match
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#4a4a4a")],
                  selectbackground=[("readonly", "#4a4a4a")],
                  selectforeground=[("readonly", "#ffffff")],
                  background=[("active", "#666666")])

        # Set the master background color to match the frames
        self.master.configure(bg="#2e2e2e")

    def _build_gui(self):
        """
        Builds and lays out all the GUI components:
          - Model selection
          - Feature selection (dropdown for each of the 10 columns)
          - Predict button
          - Output label
        """
        # Frame for main content
        content_frame = ttk.Frame(self.master)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Model selection
        model_label = ttk.Label(content_frame, text="Vyber Model:")
        model_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)

        self.model_dropdown = ttk.Combobox(
            content_frame,
            textvariable=self.model_var,
            values=list(self.models.keys()),
            state="readonly"
        )
        self.model_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Input frame for each attribute
        row_index = 1
        for col in self.FEATURE_COLS:
            display_name = self.FRIENDLY_NAMES.get(col, col)  # Fallback if missing
            lbl = ttk.Label(content_frame, text=f"{display_name}:")
            lbl.grid(row=row_index, column=0, sticky="e", padx=5, pady=3)

            if col in self.label_encoders:
                # If there's a label encoder for this column, let the user pick from those classes
                choices = list(self.label_encoders[col].classes_)
                var = tk.StringVar(value=choices[0] if choices else "")
                cmb = ttk.Combobox(content_frame, textvariable=var,
                                   values=choices, state="readonly")
                cmb.grid(row=row_index, column=1, sticky="we", padx=5, pady=3)
                self.input_vars[col] = var

            elif col in self.NUMERIC_DROPDOWNS:
                # If it's in our numeric dropdown dict, create a combobox for numeric selection
                numeric_opts = self.NUMERIC_DROPDOWNS[col]
                var = tk.StringVar(value=numeric_opts[0] if numeric_opts else "0")
                cmb = ttk.Combobox(content_frame, textvariable=var,
                                   values=numeric_opts, state="readonly")
                cmb.grid(row=row_index, column=1, sticky="we", padx=5, pady=3)
                self.input_vars[col] = var
            else:
                # Otherwise, use a text entry as fallback
                var = tk.StringVar(value="0.0")
                ent = ttk.Entry(content_frame, textvariable=var)
                ent.grid(row=row_index, column=1, sticky="we", padx=5, pady=3)
                self.input_vars[col] = var

            row_index += 1

        # Predict button
        predict_btn = ttk.Button(content_frame, text="Predikuj Cenu", command=self.predict_price)
        predict_btn.grid(row=row_index, column=0, columnspan=2, pady=10)

        # Output label
        self.output_label = ttk.Label(content_frame, text="", foreground="#00ffff", font=("Segoe UI", 10, "bold"))
        self.output_label.grid(row=row_index+1, column=0, columnspan=2, pady=5)

        # Make column 1 expandable
        content_frame.columnconfigure(1, weight=1)

    def predict_price(self):
        """
        Gathers user inputs, transforms them appropriately for the selected model,
        and displays the predicted price in the output label.
        """
        X_input = []
        for col in self.FEATURE_COLS:
            user_val = self.input_vars[col].get().strip()

            if col in self.label_encoders:
                # If there's a label encoder for this col
                try:
                    arr = self.label_encoders[col].transform([user_val])
                    X_input.append(arr[0])
                except:
                    arr = self.label_encoders[col].transform(["Missing"])
                    X_input.append(arr[0])
            elif col in self.NUMERIC_DROPDOWNS:
                # It's a numeric dropdown, interpret as float
                try:
                    X_input.append(float(user_val))
                except ValueError:
                    X_input.append(0.0)
            else:
                # fallback text input, interpret as float
                try:
                    X_input.append(float(user_val))
                except ValueError:
                    X_input.append(0.0)

        X_input = np.array(X_input).reshape(1, -1)

        selected_model = self.model_var.get()
        if selected_model not in self.models:
            self.output_label.config(text="Error: Selected model not found.")
            return

        model = self.models[selected_model]
        try:
            pred = model.predict(X_input)
        except Exception as e:
            self.output_label.config(text=f"Error in prediction: {e}")
            return

        # Extract scalar from prediction
        if isinstance(pred, np.ndarray):
            pred_value = pred.flatten()[0]
        else:
            pred_value = pred

        # Example adjustments
        if selected_model == "Neural Network":
            # Multiply NN output by 100 if needed
            pred_value *= 100
        elif selected_model == "Linear Regression":
            # If negative, make absolute
            if pred_value < 0:
                pred_value = abs(pred_value)

        self.output_label.config(text=f"Predicted Price: {pred_value:.2f}")

def main():
    """
    Main function to launch the Tkinter GUI. Loads models & encoders from pickle, then
    initializes the PricePredictorDropdownApp.
    """
    models, label_encoders = load_models_and_encoders()

    root = tk.Tk()
    app = PricePredictorDropdownApp(root, models, label_encoders)
    root.mainloop()

if __name__ == "__main__":
    main()
