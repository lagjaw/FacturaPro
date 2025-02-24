import datetime
import json

def save_report(report, file_path='daily_report.json'):
    """
    Sauvegarde le rapport journalier dans un fichier JSON.
    :param report: Dictionnaire contenant le rapport journalier
    :param file_path: Chemin où sauvegarder le fichier JSON
    """
    with open(file_path, 'w') as file:
        json.dump(report, file, indent=4)
