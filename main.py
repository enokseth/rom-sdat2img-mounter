import os
import subprocess
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Android ROM Osculter")
        self.setGeometry(100, 100, 800, 600)

        self.initUI()
        self.sdat2img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdat2img.py")
        self.mount_points = {}

    def initUI(self):
        layout = QVBoxLayout()

        # Text Zone for Logs
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # Boutons principaux
        btn_layout = QHBoxLayout()
        self.select_dir_btn = QPushButton("Select Directory")
        self.select_dir_btn.clicked.connect(self.select_directory)
        btn_layout.addWidget(self.select_dir_btn)

        # Conversion button 
        self.start_btn = QPushButton("Start SDAT2-IMG Conversion")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_processing)
        btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)

        # List Detected Images
        self.image_list = QListWidget()
        self.image_list.itemSelectionChanged.connect(self.update_buttons)
        layout.addWidget(self.image_list)

        # Actions Mount/Unmount
        action_layout = QHBoxLayout()
        self.mount_btn = QPushButton("Mount")
        self.mount_btn.setEnabled(False)
        self.mount_btn.clicked.connect(self.mount_selected_image)
        action_layout.addWidget(self.mount_btn)

        self.unmount_btn = QPushButton("Unmount")
        self.unmount_btn.setEnabled(False)
        self.unmount_btn.clicked.connect(self.unmount_selected_image)
        action_layout.addWidget(self.unmount_btn)
        layout.addLayout(action_layout)


        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
    
    

    def redirect_console(self):
            """Redirect output to the log."""
            sys.stdout = StreamRedirect(self.log)
            sys.stderr = StreamRedirect(self.log)

    def log(self, message):
        """Ajoute un message au log."""
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def decompress_brotli(self, file_path):
        """Decompress files .dat.br in .dat."""
        output_file = file_path.replace(".br", "")
        if os.path.exists(output_file):
            self.log(f"Le fichier {output_file} Already exists, deleting...")
            os.remove(output_file)
        self.log(f"Decompress of {file_path} to {output_file}...")
        subprocess.run(["brotli", "-d", file_path, "-o", output_file], check=True)
        return output_file

    def select_directory(self):
        """Ouvre une boîte de dialogue pour sélectionner un répertoire."""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.work_dir = directory
            self.log(f"Directory selectioned: {self.work_dir}")
            self.start_btn.setEnabled(True)

    def start_processing(self):
        """Démarre le traitement des fichiers dans le répertoire sélectionné."""
        if not self.work_dir or not os.path.isdir(self.work_dir):
            self.log("Error: No valid directory selected.")
            return

        self.log("Starting processing...")
        self.process_files(self.work_dir)

    def decompress_brotli(self, file_path):
        """Décompresse un fichier .dat.br en .dat."""
        output_file = file_path.replace(".br", "")
        if os.path.exists(output_file):
            self.log(f"Le fichier {output_file} Already exists, deleting...")
            os.remove(output_file)
        self.log(f"Decompress of {file_path} to {output_file}...")
        result = subprocess.run(
            ["brotli", "-d", file_path, "-o", output_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.log(result.stdout)
        if result.returncode != 0:
            self.log(f"Erreur : {result.stderr}")
            raise Exception(f"Decompression Fails... {file_path}")
        return output_file


    def convert_dat_to_img(self, dat_file, transfer_list):
        """Convertit un fichier .dat en .img en utilisant sdat2img."""
        img_file = dat_file.replace(".dat", ".img")
        self.log(f"Conversion of {dat_file} and {transfer_list} to {img_file}...")
        result = subprocess.run(
            ["python3", self.sdat2img_path, transfer_list, dat_file, img_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.log(result.stdout)
        if result.returncode != 0:
            self.log(f"Error : {result.stderr}")
            raise Exception(f"Failed conversion for {dat_file}")
        return img_file


    def mount_image(self, img_file, mount_dir):
        """Monte un fichier .img dans un répertoire."""
        os.makedirs(mount_dir, exist_ok=True)
        self.log(f"Mount of {img_file} in {mount_dir}...")
        subprocess.run(["sudo", "mount", "-o", "loop", img_file, mount_dir], check=True)

    def unmount_image(self, mount_dir):
        """Démonte un répertoire monté."""
        self.log(f"Unmount of {mount_dir}...")
        subprocess.run(["sudo", "umount", mount_dir], check=True)
        os.rmdir(mount_dir)

    def mount_selected_image(self):
        """Monter l'image sélectionnée."""
        selected_item = self.image_list.currentItem()
        if selected_item:
            img_file = selected_item.text()
            mount_dir = os.path.join(self.work_dir, f"{img_file}_mount")

            if not os.path.exists(mount_dir):
                os.makedirs(mount_dir, exist_ok=True)

            try:
                self.log(f"Montage de {img_file} dans {mount_dir}...")
                subprocess.run(["sudo", "mount", "-o", "loop", img_file, mount_dir], check=True)
                self.mount_points[img_file] = mount_dir
                self.log(f"{img_file} Successfully Mounted.")
                self.update_buttons()
            except subprocess.CalledProcessError as e:
                self.log(f"Error when mounting of{img_file} : {e}")

    def unmount_selected_image(self):
        """Démonter l'image sélectionnée."""
        selected_item = self.image_list.currentItem()
        if selected_item:
            img_file = selected_item.text()
            mount_dir = self.mount_points.get(img_file)

            if mount_dir and os.path.exists(mount_dir):
                try:
                    self.log(f"Démontage de {img_file} depuis {mount_dir}...")
                    subprocess.run(["sudo", "umount", mount_dir], check=True)
                    os.rmdir(mount_dir)
                    self.mount_points[img_file] = None
                    self.log(f"{img_file} Unmounted Successfully.")
                    self.update_buttons()
                except subprocess.CalledProcessError as e:
                    self.log(f"Error lors unmounting of {img_file} : {e}")
        
    def start_processing(self):
        """Démarre le traitement des fichiers dans le répertoire sélectionné."""
        if not self.work_dir or not os.path.isdir(self.work_dir):
            self.log("Error: No valid directory selected.")
            return

        self.log("Starting processing...")
        self.process_files(self.work_dir)
        self.log("Processing completed.")


    def process_files(self, work_dir):
        """Traite tous les fichiers dans le répertoire donné."""
        os.chdir(work_dir)
        self.image_list.clear()
        self.mount_points.clear()

        for file in os.listdir(work_dir):
            if file.endswith(".dat.br"):
                try:
                    # Étape 1 : Décompression des fichiers .dat.br
                    dat_file = self.decompress_brotli(file)

                    # Étape 2 : Conversion en .img
                    base_name = file.split(".")[0]
                    transfer_list = f"{base_name}.transfer.list"
                    if os.path.exists(transfer_list):
                        img_file = self.convert_dat_to_img(dat_file, transfer_list)

                        # Ajouter à la liste des images détectées
                        self.image_list.addItem(img_file)
                        self.mount_points[img_file] = None
                    else:
                        self.log(f"File {transfer_list} losting {file}, ingored step.")
                except Exception as e:
                    self.log(f"Error when process of {file} : {e}")

    def show_confirmation_dialog(self, mount_dir):
        """Affiche un dialogue pour demander à l'utilisateur de continuer."""
        QMessageBox.information(
            self,
            "Exploration ended",
            f"Mounted img {mount_dir} have been explored or mdoified .Press OK to unmount.",
            QMessageBox.Ok
        )

    def update_buttons(self):
            """Met à jour l'état des boutons Monter/Démonter en fonction de la sélection."""
            selected_item = self.image_list.currentItem()
            if selected_item:
                img_file = selected_item.text()
                is_mounted = self.mount_points.get(img_file) is not None
                self.mount_btn.setEnabled(not is_mounted)
                self.unmount_btn.setEnabled(is_mounted)
            else:
                self.mount_btn.setEnabled(False)
                self.unmount_btn.setEnabled(False)

    


class StreamRedirect:
    def __init__(self, log_func):
        self.log_func = log_func

    def write(self, message):
        if message.strip():  # Ignore les lignes vides
            self.log_func(message)

    def flush(self):
        pass


def run_with_sudo():
    """Relance le programme avec sudo si nécessaire."""
    if os.geteuid() != 0:  # Si le programme n'est pas exécuté avec root
        script_path = os.path.abspath(__file__)  # Obtenez le chemin absolu du script
        os.execvp("sudo", ["sudo", "python3", script_path] + sys.argv[1:])  # Relance avec sudo


def load_stylesheet(file_path):
    """Charge un fichier de style QSS."""
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Erreur lors du chargement du fichier QSS : {e}")
        return ""
    
if __name__ == "__main__":
    run_with_sudo()
    app = QApplication(sys.argv)
    stylesheet = load_stylesheet("./styles/styles.qss")
    app.setStyleSheet(stylesheet)
    window = MainWindow()
    window.redirect_console() 
    window.show()
    sys.exit(app.exec_())
