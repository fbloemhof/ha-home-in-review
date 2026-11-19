"""Generate translations/*.json and strings.json for the config/options flow and actions (single source of truth)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "custom_components" / "home_in_review"
LANGS = ("en", "nl", "de", "fr")


def t(en, nl, de, fr):
    return dict(zip(LANGS, (en, nl, de, fr), strict=True))


MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
}
TILE = {
    "sum": t("Total (increase)", "Totaal (toename)", "Summe (Zunahme)", "Total (augmentation)"),
    "mean": t("Average", "Gemiddelde", "Durchschnitt", "Moyenne"),
    "max": t("Highest", "Hoogste", "Höchstwert", "Maximum"),
    "min": t("Lowest", "Laagste", "Tiefstwert", "Minimum"),
    "hours_above": t("Hours above threshold", "Uren boven drempel", "Stunden über Schwelle", "Heures au-dessus du seuil"),
}

STEPS = {
    "init": {
        "title": t("Home in Review options", "Opties Home in Review", "Home in Review Optionen", "Options Home in Review"),
        "menu": {
            "general": t("Schedule and notifications", "Planning en meldingen", "Zeitplan und Benachrichtigungen", "Planification et notifications"),
            "energy": t("Energy, costs and heat pump", "Energie, kosten en warmtepomp", "Energie, Kosten und Wärmepumpe", "Énergie, coûts et pompe à chaleur"),
            "climate": t("Indoor climate and weather", "Binnenklimaat en weer", "Raumklima und Wetter", "Climat intérieur et météo"),
            "car": t("Car (TeslaMate)", "Auto (TeslaMate)", "Auto (TeslaMate)", "Voiture (TeslaMate)"),
            "ai": t("AI summary", "AI-samenvatting", "KI-Zusammenfassung", "Résumé IA"),
            "tile_add": t("Add your own figure", "Eigen cijfer toevoegen", "Eigene Kennzahl hinzufügen", "Ajouter un chiffre"),
            "tile_remove": t("Remove your own figures", "Eigen cijfers verwijderen", "Eigene Kennzahlen entfernen", "Supprimer des chiffres"),
            "save": t("Save and close", "Opslaan en sluiten", "Speichern und schließen", "Enregistrer et fermer"),
        },
    },
    "general": {
        "title": t("Schedule and notifications", "Planning en meldingen", "Zeitplan und Benachrichtigungen", "Planification et notifications"),
        "data": {
            "notify_services": t("Notify when a report is ready", "Melding sturen als een rapport klaar is", "Benachrichtigen, wenn ein Bericht fertig ist", "Notifier quand un rapport est prêt"),
            "report_day": t("Day of the month", "Dag van de maand", "Tag des Monats", "Jour du mois"),
            "report_time": t("Time", "Tijd", "Uhrzeit", "Heure"),
            "year_start_month": t("Year review starts in", "Jaaroverzicht begint in", "Jahresrückblick beginnt im", "Le bilan annuel commence en"),
        },
        "data_description": {
            "notify_services": t("The notification opens the report.", "De melding opent het rapport.", "Die Benachrichtigung öffnet den Bericht.", "La notification ouvre le rapport."),
            "report_day": t("Last month's report is made on this day.", "Op deze dag wordt het rapport over de vorige maand gemaakt.", "An diesem Tag wird der Bericht des Vormonats erstellt.", "Le rapport du mois précédent est créé ce jour-là."),
            "year_start_month": t("January for a calendar year; for example July for a heating season or the month your energy contract starts.", "Januari voor een kalenderjaar; bijvoorbeeld juli voor een stookseizoen of de maand waarin je energiecontract begint.", "Januar für ein Kalenderjahr; zum Beispiel Juli für eine Heizperiode oder den Beginn Ihres Energievertrags.", "Janvier pour une année civile ; par exemple juillet pour une saison de chauffe ou le début de votre contrat."),
        },
    },
    "energy": {
        "title": t("Energy, costs and heat pump", "Energie, kosten en warmtepomp", "Energie, Kosten und Wärmepumpe", "Énergie, coûts et pompe à chaleur"),
        "data": {
            "fixed_costs_daily": t("Fixed energy costs per day", "Vaste energiekosten per dag", "Fixe Energiekosten pro Tag", "Coûts fixes par jour"),
            "fixed_costs_monthly": t("Fixed energy costs per month", "Vaste energiekosten per maand", "Fixe Energiekosten pro Monat", "Coûts fixes par mois"),
            "max_hourly_kwh": t("Largest plausible grid use per hour", "Grootst mogelijke netafname per uur", "Größter plausibler Netzbezug pro Stunde", "Consommation horaire maximale plausible"),
            "heat_pump_devices": t("Heat pump (devices from the energy dashboard)", "Warmtepomp (apparaten uit het energiedashboard)", "Wärmepumpe (Geräte aus dem Energie-Dashboard)", "Pompe à chaleur (appareils du tableau énergie)"),
            "heat_pump_heat_sensor": t("Heat delivered by the heat pump", "Door de warmtepomp geleverde warmte", "Von der Wärmepumpe gelieferte Wärme", "Chaleur fournie par la pompe à chaleur"),
        },
        "data_description": {
            "fixed_costs_daily": t("Optional, including tax: standing charges and grid fees.", "Optioneel, inclusief btw: vaste leveringskosten en netbeheer.", "Optional, inkl. Steuern: Grundgebühr und Netzentgelte.", "Facultatif, TTC : abonnement et frais de réseau."),
            "fixed_costs_monthly": t("Optional, including tax. Use a negative amount for a fixed tax credit.", "Optioneel, inclusief btw. Gebruik een negatief bedrag voor een vaste belastingkorting.", "Optional, inkl. Steuern. Negativ für eine feste Steuergutschrift.", "Facultatif, TTC. Montant négatif pour un crédit d'impôt fixe."),
            "max_hourly_kwh": t("Meter jumps above this per hour are treated as glitches. Roughly your connection: 3 × 25 A ≈ 17 kWh, 3 × 35 A ≈ 24 kWh, 1 × 40 A ≈ 9 kWh.", "Sprongen in de meterstand boven deze waarde per uur gelden als storing. Ongeveer je aansluiting: 3 × 25 A ≈ 17 kWh, 3 × 35 A ≈ 24 kWh, 1 × 40 A ≈ 9 kWh.", "Zählersprünge darüber gelten als Störung. Etwa Ihr Anschluss: 3 × 25 A ≈ 17 kWh, 3 × 35 A ≈ 24 kWh.", "Les sauts au-delà sont considérés comme des erreurs. Environ votre raccordement : 3 × 25 A ≈ 17 kWh, 3 × 35 A ≈ 24 kWh."),
            "heat_pump_devices": t("Adds a heat pump slide with electricity per degree day.", "Voegt een warmtepompdia toe met stroom per graaddag.", "Fügt eine Wärmepumpen-Folie mit Strom pro Gradtag hinzu.", "Ajoute une diapositive pompe à chaleur avec l'électricité par degré-jour."),
            "heat_pump_heat_sensor": t("Optional energy sensor (total) for heat output; adds the COP.", "Optionele energiesensor (totaal) voor de warmteafgifte; voegt de COP toe.", "Optionaler Energiesensor (Summe) für die Wärmeabgabe; ergänzt den COP.", "Capteur d'énergie (total) facultatif pour la chaleur produite ; ajoute le COP."),
        },
    },
    "climate": {
        "title": t("Indoor climate and weather", "Binnenklimaat en weer", "Raumklima und Wetter", "Climat intérieur et météo"),
        "data": {
            "excluded_areas": t("Areas that are not indoors", "Ruimtes die niet binnen zijn", "Bereiche, die nicht drinnen sind", "Pièces qui ne sont pas à l'intérieur"),
            "outdoor_sensor": t("Outdoor temperature sensor", "Buitentemperatuursensor", "Außentemperatursensor", "Capteur de température extérieure"),
            "use_open_meteo": t("Use Open-Meteo for weather", "Open-Meteo gebruiken voor het weer", "Open-Meteo für das Wetter nutzen", "Utiliser Open-Meteo pour la météo"),
        },
        "data_description": {
            "excluded_areas": t("Sensors in these areas are left out of the indoor climate. Empty = count everything.", "Sensoren in deze ruimtes tellen niet mee voor het binnenklimaat. Leeg = alles meetellen.", "Sensoren in diesen Bereichen zählen nicht zum Raumklima. Leer = alles zählen.", "Les capteurs de ces pièces sont exclus. Vide = tout compter."),
            "outdoor_sensor": t("Optional. Any temperature sensor with history; replaces the modelled temperature.", "Optioneel. Elke temperatuursensor met historie; vervangt de modeltemperatuur.", "Optional. Jeder Temperatursensor mit Verlauf; ersetzt die Modelltemperatur.", "Facultatif. Tout capteur avec historique ; remplace la température modélisée."),
            "use_open_meteo": t("Free weather archive for your area (location rounded to ~10 km). Off: only your own sensor, without normals, rain or sunshine.", "Gratis weerarchief voor jouw omgeving (locatie afgerond op ~10 km). Uit: alleen je eigen sensor, zonder normalen, neerslag of zon.", "Kostenloses Wetterarchiv für Ihre Gegend (Standort auf ~10 km gerundet). Aus: nur Ihr eigener Sensor.", "Archive météo gratuite pour votre région (position arrondie à ~10 km). Désactivé : seulement votre capteur."),
        },
    },
    "car": {
        "title": t("Car (TeslaMate)", "Auto (TeslaMate)", "Auto (TeslaMate)", "Voiture (TeslaMate)"),
        "description": t("Reads TeslaMate through its Grafana. Create a service account with the Viewer role in Grafana and paste its token.", "Leest TeslaMate via de bijbehorende Grafana. Maak in Grafana een serviceaccount met de rol Viewer en plak de token.", "Liest TeslaMate über dessen Grafana. Legen Sie in Grafana ein Dienstkonto mit der Rolle Viewer an und fügen Sie das Token ein.", "Lit TeslaMate via son Grafana. Créez un compte de service avec le rôle Viewer et collez le jeton."),
        "data": {
            "teslamate_grafana_url": t("Grafana URL", "Grafana-URL", "Grafana-URL", "URL de Grafana"),
            "teslamate_grafana_token": t("Service account token", "Serviceaccount-token", "Dienstkonto-Token", "Jeton du compte de service"),
            "teslamate_home_geofence": t("Name of your home geofence", "Naam van je thuis-geofence", "Name Ihres Zuhause-Geofence", "Nom de votre geofence domicile"),
        },
        "data_description": {
            "teslamate_home_geofence": t("Used to count charging at home. Empty: a geofence called Home (or its translation).", "Om laden thuis te tellen. Leeg: een geofence met de naam Home of Thuis.", "Um das Laden zu Hause zu zählen. Leer: ein Geofence namens Home oder Zuhause.", "Pour compter la recharge à domicile. Vide : un geofence nommé Home ou Maison."),
        },
    },
    "ai": {
        "title": t("AI summary", "AI-samenvatting", "KI-Zusammenfassung", "Résumé IA"),
        "description": t("Optional: a short written summary at the start of each report, by your own AI Task entity. Only the report's figures are sent.", "Optioneel: een korte geschreven samenvatting aan het begin van elk rapport, door je eigen AI Task-entiteit. Alleen de cijfers uit het rapport worden verstuurd.", "Optional: eine kurze Zusammenfassung am Anfang jedes Berichts durch Ihre eigene KI-Aufgaben-Entität. Nur die Zahlen des Berichts werden gesendet.", "Facultatif : un court résumé au début de chaque rapport, par votre propre entité AI Task. Seuls les chiffres du rapport sont envoyés."),
        "data": {
            "ai_task_entity": t("AI Task entity", "AI Task-entiteit", "KI-Aufgaben-Entität", "Entité AI Task"),
            "ai_instructions": t("Extra instructions", "Extra instructies", "Zusätzliche Anweisungen", "Instructions supplémentaires"),
        },
        "data_description": {
            "ai_instructions": t("Optional, e.g. the tone of voice or who lives in the house.", "Optioneel, bijvoorbeeld de toon of wie er in huis wonen.", "Optional, z. B. Tonfall oder wer im Haus wohnt.", "Facultatif, par ex. le ton ou qui habite la maison."),
        },
    },
    "tile_add": {
        "title": t("Add your own figure", "Eigen cijfer toevoegen", "Eigene Kennzahl hinzufügen", "Ajouter un chiffre"),
        "description": t("Shown on a 'Your figures' slide, compared with earlier months.", "Verschijnt op een dia 'Eigen cijfers', vergeleken met eerdere maanden.", "Erscheint auf einer Folie 'Eigene Kennzahlen', verglichen mit früheren Monaten.", "Affiché sur une diapositive « Vos chiffres », comparé aux mois précédents."),
        "data": {
            "name": t("Name", "Naam", "Name", "Nom"),
            "statistic": t("Statistic", "Statistiek", "Statistik", "Statistique"),
            "type": t("Calculation", "Berekening", "Berechnung", "Calcul"),
            "threshold": t("Threshold (for hours above)", "Drempel (voor uren boven)", "Schwelle (für Stunden über)", "Seuil (pour heures au-dessus)"),
            "unit": t("Unit", "Eenheid", "Einheit", "Unité"),
            "decimals": t("Decimals", "Decimalen", "Nachkommastellen", "Décimales"),
        },
    },
    "tile_remove": {
        "title": t("Remove your own figures", "Eigen cijfers verwijderen", "Eigene Kennzahlen entfernen", "Supprimer des chiffres"),
        "data": {"tiles": t("Figures to remove", "Te verwijderen cijfers", "Zu entfernende Kennzahlen", "Chiffres à supprimer")},
    },
}

CONFIG = {
    "abort": {"single_instance_allowed": t("Home in Review is already set up.", "Home in Review is al ingesteld.", "Home in Review ist bereits eingerichtet.", "Home in Review est déjà configuré.")},
    "user": {
        "title": t("Home in Review", "Home in Review", "Home in Review", "Home in Review"),
        "description": t("A monthly report of your home, made from your energy dashboard, local weather and indoor sensors. Reports appear in the sidebar.", "Een maandrapport van je huis, gemaakt van je energiedashboard, het lokale weer en je binnensensoren. Rapporten verschijnen in de zijbalk.", "Ein Monatsbericht Ihres Zuhauses aus Energie-Dashboard, lokalem Wetter und Innensensoren. Berichte erscheinen in der Seitenleiste.", "Un rapport mensuel de votre maison à partir du tableau énergie, de la météo locale et des capteurs intérieurs. Les rapports apparaissent dans la barre latérale."),
        "data": {"backfill_months": t("Months to generate from history", "Aantal maanden uit de historie maken", "Monate aus dem Verlauf erstellen", "Mois à générer depuis l'historique")},
        "data_description": {"backfill_months": t("Earlier months are generated in the background from long-term statistics. Use 0 to skip.", "Eerdere maanden worden op de achtergrond gemaakt uit de langetermijnstatistieken. Gebruik 0 om over te slaan.", "Frühere Monate werden im Hintergrund aus Langzeitstatistiken erstellt. 0 zum Überspringen.", "Les mois précédents sont générés en arrière-plan. 0 pour ignorer.")},
    },
}

SERVICES = {
    "generate": {
        "name": t("Generate report", "Rapport maken", "Bericht erstellen", "Générer un rapport"),
        "description": t("Collects (or re-collects) the report for one month.", "Verzamelt (opnieuw) het rapport voor één maand.", "Erstellt den Bericht für einen Monat (neu).", "Génère (à nouveau) le rapport d'un mois."),
        "fields": {
            "month": (t("Month", "Maand", "Monat", "Mois"), t("As YYYY-MM. Defaults to last month.", "Als JJJJ-MM. Standaard de vorige maand.", "Als JJJJ-MM. Standard: Vormonat.", "Au format AAAA-MM. Par défaut le mois dernier.")),
            "notify": (t("Notify", "Melden", "Benachrichtigen", "Notifier"), t("Send the configured notifications.", "Stuur de ingestelde meldingen.", "Die eingerichteten Benachrichtigungen senden.", "Envoyer les notifications configurées.")),
        },
    },
    "backfill": {
        "name": t("Backfill reports", "Eerdere rapporten maken", "Frühere Berichte erstellen", "Générer les rapports passés"),
        "description": t("Generates reports for earlier months in the background.", "Maakt rapporten voor eerdere maanden op de achtergrond.", "Erstellt Berichte für frühere Monate im Hintergrund.", "Génère les rapports des mois précédents en arrière-plan."),
        "fields": {
            "months": (t("Months", "Maanden", "Monate", "Mois"), t("How many months to look back.", "Hoeveel maanden terug.", "Wie viele Monate zurück.", "Combien de mois en arrière.")),
            "overwrite": (t("Overwrite", "Overschrijven", "Überschreiben", "Écraser"), t("Also re-make months that already have a report (after an update or a change in options).", "Maak ook maanden opnieuw die al een rapport hebben (na een update of gewijzigde opties).", "Auch vorhandene Monate neu erstellen (nach einem Update oder geänderten Optionen).", "Régénérer aussi les mois existants (après une mise à jour ou un changement d'options).")),
        },
    },
}


def pick(node, lang):
    if isinstance(node, dict) and set(node) == set(LANGS):
        return node[lang]
    if isinstance(node, dict):
        return {k: pick(v, lang) for k, v in node.items()}
    return node


for lang in LANGS:
    steps = {k: pick(v, lang) for k, v in STEPS.items()}
    doc = {
        "config": {"abort": pick(CONFIG["abort"], lang), "step": {"user": pick(CONFIG["user"], lang)}},
        "options": {"step": steps},
        "selector": {
            "month": {"options": {str(i + 1): m for i, m in enumerate(MONTHS[lang])}},
            "tile_type": {"options": {k: v[lang] for k, v in TILE.items()}},
        },
        "services": {k: {"name": v["name"][lang], "description": v["description"][lang],
                         "fields": {f: {"name": n[lang], "description": d[lang]} for f, (n, d) in v["fields"].items()}}
                     for k, v in SERVICES.items()},
    }
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    (OUT / "translations" / f"{lang}.json").write_text(text, encoding="utf-8")
    if lang == "en":
        (OUT / "strings.json").write_text(text, encoding="utf-8")
print("written", ", ".join(LANGS))
