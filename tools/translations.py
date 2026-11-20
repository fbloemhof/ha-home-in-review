"""Generate translations/*.json and strings.json for the config/options flow and actions (single source of truth)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
    "days_above": t("Days above threshold", "Dagen boven drempel", "Tage über Schwelle", "Jours au-dessus du seuil"),
    "runs_above": t("Runs (from power above threshold)", "Beurten (vermogen boven drempel)", "Durchgänge (Leistung über Schwelle)", "Cycles (puissance au-dessus du seuil)"),
}

STEPS = {'init': {'title': {'en': 'Home in Review options',
                    'nl': 'Opties Home in Review',
                    'de': 'Home in Review Optionen',
                    'fr': 'Options Home in Review'},
          'menu_options': {'settings': {'en': 'Settings',
                                        'nl': 'Instellingen',
                                        'de': 'Einstellungen',
                                        'fr': 'Paramètres'},
                           'tile_add': {'en': 'Add your own figure',
                                        'nl': 'Eigen cijfer toevoegen',
                                        'de': 'Eigene Kennzahl hinzufügen',
                                        'fr': 'Ajouter un chiffre'},
                           'tile_remove': {'en': 'Remove your own figures',
                                           'nl': 'Eigen cijfers verwijderen',
                                           'de': 'Eigene Kennzahlen entfernen',
                                           'fr': 'Supprimer des chiffres'}}},
 'settings': {'title': {'en': 'Home in Review options',
                        'nl': 'Opties Home in Review',
                        'de': 'Home in Review Optionen',
                        'fr': 'Options Home in Review'},
              'description': {'en': 'Open a section to change it. Saving closes this window.',
                              'nl': 'Klap een onderdeel open om het te wijzigen. Opslaan sluit dit venster.',
                              'de': 'Öffnen Sie einen Abschnitt, um ihn zu ändern. Speichern schließt dieses '
                                    'Fenster.',
                              'fr': 'Ouvrez une section pour la modifier. Enregistrer ferme cette fenêtre.'},
              'sections': {'general': {'name': {'en': 'Schedule and notifications',
                                                'nl': 'Planning en meldingen',
                                                'de': 'Zeitplan und Benachrichtigungen',
                                                'fr': 'Planification et notifications'},
                                       'data': {'notify_services': {'en': 'Notify when a report is ready',
                                                                    'nl': 'Melding sturen als een rapport klaar is',
                                                                    'de': 'Benachrichtigen, wenn ein Bericht fertig '
                                                                          'ist',
                                                                    'fr': 'Notifier quand un rapport est prêt'},
                                                'report_day': {'en': 'Day of the month',
                                                               'nl': 'Dag van de maand',
                                                               'de': 'Tag des Monats',
                                                               'fr': 'Jour du mois'},
                                                'report_time': {'en': 'Time',
                                                                'nl': 'Tijd',
                                                                'de': 'Uhrzeit',
                                                                'fr': 'Heure'},
                                                'year_start_month': {'en': 'Year review starts in',
                                                                     'nl': 'Jaaroverzicht begint in',
                                                                     'de': 'Jahresrückblick beginnt im',
                                                                     'fr': 'Le bilan annuel commence en'}},
                                       'data_description': {'notify_services': {'en': 'The notification opens the '
                                                                                      'report.',
                                                                                'nl': 'De melding opent het rapport.',
                                                                                'de': 'Die Benachrichtigung öffnet '
                                                                                      'den Bericht.',
                                                                                'fr': 'La notification ouvre le '
                                                                                      'rapport.'},
                                                            'report_day': {'en': "Last month's report is made on "
                                                                                 'this day.',
                                                                           'nl': 'Op deze dag wordt het rapport over '
                                                                                 'de vorige maand gemaakt.',
                                                                           'de': 'An diesem Tag wird der Bericht des '
                                                                                 'Vormonats erstellt.',
                                                                           'fr': 'Le rapport du mois précédent est '
                                                                                 'créé ce jour-là.'},
                                                            'year_start_month': {'en': 'January for a calendar year; '
                                                                                       'for example July for a '
                                                                                       'heating season or the month '
                                                                                       'your energy contract starts.',
                                                                                 'nl': 'Januari voor een '
                                                                                       'kalenderjaar; bijvoorbeeld '
                                                                                       'juli voor een stookseizoen '
                                                                                       'of de maand waarin je '
                                                                                       'energiecontract begint.',
                                                                                 'de': 'Januar für ein Kalenderjahr; '
                                                                                       'zum Beispiel Juli für eine '
                                                                                       'Heizperiode oder den Beginn '
                                                                                       'Ihres Energievertrags.',
                                                                                 'fr': 'Janvier pour une année '
                                                                                       'civile ; par exemple juillet '
                                                                                       'pour une saison de chauffe '
                                                                                       'ou le début de votre '
                                                                                       'contrat.'}}},
                           'energy': {'name': {'en': 'Energy, costs and heat pump',
                                               'nl': 'Energie, kosten en warmtepomp',
                                               'de': 'Energie, Kosten und Wärmepumpe',
                                               'fr': 'Énergie, coûts et pompe à chaleur'},
                                      'data': {'fixed_costs_daily': {'en': 'Fixed energy costs per day',
                                                                     'nl': 'Vaste energiekosten per dag',
                                                                     'de': 'Fixe Energiekosten pro Tag',
                                                                     'fr': 'Coûts fixes par jour'},
                                               'fixed_costs_monthly': {'en': 'Fixed energy costs per month',
                                                                       'nl': 'Vaste energiekosten per maand',
                                                                       'de': 'Fixe Energiekosten pro Monat',
                                                                       'fr': 'Coûts fixes par mois'},
                                               'max_hourly_kwh': {'en': 'Largest plausible grid use per hour',
                                                                  'nl': 'Grootst mogelijke netafname per uur',
                                                                  'de': 'Größter plausibler Netzbezug pro Stunde',
                                                                  'fr': 'Consommation horaire maximale plausible'},
                                               'heat_pump_devices': {'en': 'Heat pump electricity',
                                                                     'nl': 'Stroom van de warmtepomp',
                                                                     'de': 'Strom der Wärmepumpe',
                                                                     'fr': 'Électricité de la pompe à chaleur'},
                                               'heat_pump_heat_sensor': {'en': 'Heat delivered by the heat pump',
                                                                         'nl': 'Door de warmtepomp geleverde warmte',
                                                                         'de': 'Von der Wärmepumpe gelieferte Wärme',
                                                                         'fr': 'Chaleur fournie par la pompe à '
                                                                               'chaleur'}},
                                      'data_description': {'fixed_costs_daily': {'en': 'Optional, including tax: '
                                                                                       'standing charges and grid '
                                                                                       'fees.',
                                                                                 'nl': 'Optioneel, inclusief btw: '
                                                                                       'vaste leveringskosten en '
                                                                                       'netbeheer.',
                                                                                 'de': 'Optional, inkl. Steuern: '
                                                                                       'Grundgebühr und '
                                                                                       'Netzentgelte.',
                                                                                 'fr': 'Facultatif, TTC : abonnement '
                                                                                       'et frais de réseau.'},
                                                           'fixed_costs_monthly': {'en': 'Optional, including tax. '
                                                                                         'Use a negative amount for '
                                                                                         'a fixed tax credit.',
                                                                                   'nl': 'Optioneel, inclusief btw. '
                                                                                         'Gebruik een negatief '
                                                                                         'bedrag voor een vaste '
                                                                                         'belastingkorting.',
                                                                                   'de': 'Optional, inkl. Steuern. '
                                                                                         'Negativ für eine feste '
                                                                                         'Steuergutschrift.',
                                                                                   'fr': 'Facultatif, TTC. Montant '
                                                                                         'négatif pour un crédit '
                                                                                         "d'impôt fixe."},
                                                           'max_hourly_kwh': {'en': 'Meter jumps above this per hour '
                                                                                    'are treated as glitches. '
                                                                                    'Roughly your connection: 3 × 25 '
                                                                                    'A ≈ 17 kWh, 3 × 35 A ≈ 24 kWh, '
                                                                                    '1 × 40 A ≈ 9 kWh.',
                                                                              'nl': 'Sprongen in de meterstand boven '
                                                                                    'deze waarde per uur gelden als '
                                                                                    'storing. Ongeveer je '
                                                                                    'aansluiting: 3 × 25 A ≈ 17 kWh, '
                                                                                    '3 × 35 A ≈ 24 kWh, 1 × 40 A ≈ 9 '
                                                                                    'kWh.',
                                                                              'de': 'Zählersprünge darüber gelten '
                                                                                    'als Störung. Etwa Ihr '
                                                                                    'Anschluss: 3 × 25 A ≈ 17 kWh, 3 '
                                                                                    '× 35 A ≈ 24 kWh.',
                                                                              'fr': 'Les sauts au-delà sont '
                                                                                    'considérés comme des erreurs. '
                                                                                    'Environ votre raccordement : 3 '
                                                                                    '× 25 A ≈ 17 kWh, 3 × 35 A ≈ 24 '
                                                                                    'kWh.'},
                                                           'heat_pump_devices': {'en': 'Any brand: one or more '
                                                                                       'energy sensors (the heat '
                                                                                       "pump's own integration, a "
                                                                                       'kWh meter or smart plug, '
                                                                                       'e.g. compressor and backup '
                                                                                       'heater). Adds a heat pump '
                                                                                       'slide with electricity per '
                                                                                       'degree day.',
                                                                                 'nl': 'Elk merk: een of meer '
                                                                                       'energiesensoren (de eigen '
                                                                                       'integratie van de '
                                                                                       'warmtepomp, een kWh-meter of '
                                                                                       'slimme stekker, bijv. '
                                                                                       'compressor en backupheater). '
                                                                                       'Voegt een warmtepompdia toe '
                                                                                       'met stroom per graaddag.',
                                                                                 'de': 'Jede Marke: ein oder mehrere '
                                                                                       'Energiesensoren (Integration '
                                                                                       'der Wärmepumpe, Zähler oder '
                                                                                       'Steckdose, z. B. Verdichter '
                                                                                       'und Heizstab). Fügt eine '
                                                                                       'Wärmepumpen-Folie hinzu.',
                                                                                 'fr': 'Toute marque : un ou '
                                                                                       "plusieurs capteurs d'énergie "
                                                                                       '(intégration de la pompe, '
                                                                                       'compteur ou prise, p. ex. '
                                                                                       'compresseur et appoint). '
                                                                                       'Ajoute une diapositive pompe '
                                                                                       'à chaleur.'},
                                                           'heat_pump_heat_sensor': {'en': 'Optional: energy sensors '
                                                                                           'for heat delivered (many '
                                                                                           'brands report heating '
                                                                                           'and hot water '
                                                                                           'separately; choose '
                                                                                           'both). Adds the COP.',
                                                                                     'nl': 'Optioneel: '
                                                                                           'energiesensoren voor de '
                                                                                           'geleverde warmte (veel '
                                                                                           'merken melden verwarming '
                                                                                           'en tapwater apart; kies '
                                                                                           'dan beide). Voegt de COP '
                                                                                           'toe.',
                                                                                     'de': 'Optional: '
                                                                                           'Energiesensoren für die '
                                                                                           'gelieferte Wärme (oft '
                                                                                           'getrennt für Heizung und '
                                                                                           'Warmwasser; beide '
                                                                                           'wählen). Ergänzt den '
                                                                                           'COP.',
                                                                                     'fr': 'Facultatif : capteurs de '
                                                                                           'chaleur fournie (souvent '
                                                                                           'chauffage et eau chaude '
                                                                                           'séparés ; choisissez les '
                                                                                           'deux). Ajoute le COP.'}}},
                           'climate': {'name': {'en': 'Indoor climate and weather',
                                                'nl': 'Binnenklimaat en weer',
                                                'de': 'Raumklima und Wetter',
                                                'fr': 'Climat intérieur et météo'},
                                       'data': {'excluded_areas': {'en': 'Areas that are not indoors',
                                                                   'nl': 'Ruimtes die niet binnen zijn',
                                                                   'de': 'Bereiche, die nicht drinnen sind',
                                                                   'fr': "Pièces qui ne sont pas à l'intérieur"},
                                                'outdoor_sensor': {'en': 'Outdoor temperature sensor',
                                                                   'nl': 'Buitentemperatuursensor',
                                                                   'de': 'Außentemperatursensor',
                                                                   'fr': 'Capteur de température extérieure'},
                                                'use_open_meteo': {'en': 'Use Open-Meteo for weather',
                                                                   'nl': 'Open-Meteo gebruiken voor het weer',
                                                                   'de': 'Open-Meteo für das Wetter nutzen',
                                                                   'fr': 'Utiliser Open-Meteo pour la météo'}},
                                       'data_description': {'excluded_areas': {'en': 'Sensors in these areas are '
                                                                                     'left out of the indoor '
                                                                                     'climate. Empty = count '
                                                                                     'everything.',
                                                                               'nl': 'Sensoren in deze ruimtes '
                                                                                     'tellen niet mee voor het '
                                                                                     'binnenklimaat. Leeg = alles '
                                                                                     'meetellen.',
                                                                               'de': 'Sensoren in diesen Bereichen '
                                                                                     'zählen nicht zum Raumklima. '
                                                                                     'Leer = alles zählen.',
                                                                               'fr': 'Les capteurs de ces pièces '
                                                                                     'sont exclus. Vide = tout '
                                                                                     'compter.'},
                                                            'outdoor_sensor': {'en': 'Optional. Any temperature '
                                                                                     'sensor with history; replaces '
                                                                                     'the modelled temperature.',
                                                                               'nl': 'Optioneel. Elke '
                                                                                     'temperatuursensor met '
                                                                                     'historie; vervangt de '
                                                                                     'modeltemperatuur.',
                                                                               'de': 'Optional. Jeder '
                                                                                     'Temperatursensor mit Verlauf; '
                                                                                     'ersetzt die Modelltemperatur.',
                                                                               'fr': 'Facultatif. Tout capteur avec '
                                                                                     'historique ; remplace la '
                                                                                     'température modélisée.'},
                                                            'use_open_meteo': {'en': 'Free weather archive for your '
                                                                                     'area (location rounded to ~10 '
                                                                                     'km). Off: only your own '
                                                                                     'sensor, without normals, rain '
                                                                                     'or sunshine.',
                                                                               'nl': 'Gratis weerarchief voor jouw '
                                                                                     'omgeving (locatie afgerond op '
                                                                                     '~10 km). Uit: alleen je eigen '
                                                                                     'sensor, zonder normalen, '
                                                                                     'neerslag of zon.',
                                                                               'de': 'Kostenloses Wetterarchiv für '
                                                                                     'Ihre Gegend (Standort auf ~10 '
                                                                                     'km gerundet). Aus: nur Ihr '
                                                                                     'eigener Sensor.',
                                                                               'fr': 'Archive météo gratuite pour '
                                                                                     'votre région (position '
                                                                                     'arrondie à ~10 km). Désactivé '
                                                                                     ': seulement votre capteur.'}}},
                           'car': {'name': {'en': 'Car', 'nl': 'Auto', 'de': 'Auto', 'fr': 'Voiture'},
                                   'data': {'car_odometers': {'en': 'Odometer (one per car)',
                                                              'nl': 'Kilometerteller (één per auto)',
                                                              'de': 'Kilometerzähler (einer pro Auto)',
                                                              'fr': 'Compteur kilométrique (un par voiture)'},
                                            'car_chargers': {'en': 'Charger energy',
                                                             'nl': 'Energie van de laadpaal',
                                                             'de': 'Energie der Ladestation',
                                                             'fr': 'Énergie de la borne'},
                                            'teslamate_grafana_url': {'en': 'Grafana URL',
                                                                      'nl': 'Grafana-URL',
                                                                      'de': 'Grafana-URL',
                                                                      'fr': 'URL de Grafana'},
                                            'teslamate_grafana_token': {'en': 'Service account token',
                                                                        'nl': 'Serviceaccount-token',
                                                                        'de': 'Dienstkonto-Token',
                                                                        'fr': 'Jeton du compte de service'},
                                            'teslamate_home_geofence': {'en': 'Name of your home geofence',
                                                                        'nl': 'Naam van je thuis-geofence',
                                                                        'de': 'Name Ihres Zuhause-Geofence',
                                                                        'fr': 'Nom de votre geofence domicile'}},
                                   'data_description': {'teslamate_home_geofence': {'en': 'Used to count charging at '
                                                                                          'home. Empty: a geofence '
                                                                                          'called Home (or its '
                                                                                          'translation).',
                                                                                    'nl': 'Om laden thuis te tellen. '
                                                                                          'Leeg: een geofence met de '
                                                                                          'naam Home of Thuis.',
                                                                                    'de': 'Um das Laden zu Hause zu '
                                                                                          'zählen. Leer: ein '
                                                                                          'Geofence namens Home oder '
                                                                                          'Zuhause.',
                                                                                    'fr': 'Pour compter la recharge '
                                                                                          'à domicile. Vide : un '
                                                                                          'geofence nommé Home ou '
                                                                                          'Maison.'}},
                                   'description': {'en': "Any car: choose its odometer sensor (from the car's own "
                                                         'integration) and the energy sensor of your charger. With '
                                                         'TeslaMate you get more (trips, charging at home and '
                                                         'elsewhere, Wh/km): fill in its Grafana URL and the token '
                                                         'of a Grafana service account with the Viewer role.',
                                                   'nl': 'Elke auto: kies de kilometerteller (uit de integratie van '
                                                         'je auto) en de energiesensor van je laadpaal. Met '
                                                         'TeslaMate krijg je meer (ritten, thuis en elders laden, '
                                                         'Wh/km): vul de URL van de bijbehorende Grafana in en de '
                                                         'token van een serviceaccount met de rol Viewer.',
                                                   'de': 'Jedes Auto: wählen Sie den Kilometerzähler (aus der '
                                                         'Integration Ihres Autos) und den Energiesensor Ihrer '
                                                         'Ladestation. Mit TeslaMate erhalten Sie mehr: Grafana-URL '
                                                         'und das Token eines Dienstkontos mit der Rolle Viewer '
                                                         'eintragen.',
                                                   'fr': 'Toute voiture : choisissez le compteur kilométrique (de '
                                                         "l'intégration de la voiture) et le capteur d'énergie de "
                                                         'votre borne. Avec TeslaMate vous obtenez plus : URL de '
                                                         "Grafana et jeton d'un compte de service Viewer."}},
                           'ai': {'name': {'en': 'AI summary',
                                           'nl': 'AI-samenvatting',
                                           'de': 'KI-Zusammenfassung',
                                           'fr': 'Résumé IA'},
                                  'data': {'ai_task_entity': {'en': 'AI Task entity',
                                                              'nl': 'AI Task-entiteit',
                                                              'de': 'KI-Aufgaben-Entität',
                                                              'fr': 'Entité AI Task'},
                                           'ai_instructions': {'en': 'Extra instructions',
                                                               'nl': 'Extra instructies',
                                                               'de': 'Zusätzliche Anweisungen',
                                                               'fr': 'Instructions supplémentaires'}},
                                  'data_description': {'ai_instructions': {'en': 'Optional, e.g. the tone of voice '
                                                                                 'or who lives in the house.',
                                                                           'nl': 'Optioneel, bijvoorbeeld de toon of '
                                                                                 'wie er in huis wonen.',
                                                                           'de': 'Optional, z. B. Tonfall oder wer '
                                                                                 'im Haus wohnt.',
                                                                           'fr': 'Facultatif, par ex. le ton ou qui '
                                                                                 'habite la maison.'}},
                                  'description': {'en': 'Optional: a short written summary at the start of each '
                                                        "report, by your own AI Task entity. Only the report's "
                                                        'figures are sent.',
                                                  'nl': 'Optioneel: een korte geschreven samenvatting aan het begin '
                                                        'van elk rapport, door je eigen AI Task-entiteit. Alleen de '
                                                        'cijfers uit het rapport worden verstuurd.',
                                                  'de': 'Optional: eine kurze Zusammenfassung am Anfang jedes '
                                                        'Berichts durch Ihre eigene KI-Aufgaben-Entität. Nur die '
                                                        'Zahlen des Berichts werden gesendet.',
                                                  'fr': 'Facultatif : un court résumé au début de chaque rapport, '
                                                        'par votre propre entité AI Task. Seuls les chiffres du '
                                                        'rapport sont envoyés.'}}}},
 'tile_add': {'title': {'en': 'Add your own figure',
                        'nl': 'Eigen cijfer toevoegen',
                        'de': 'Eigene Kennzahl hinzufügen',
                        'fr': 'Ajouter un chiffre'},
              'description': {'en': "Shown on a 'Your figures' slide, compared with earlier months.",
                              'nl': "Verschijnt op een dia 'Eigen cijfers', vergeleken met eerdere maanden.",
                              'de': "Erscheint auf einer Folie 'Eigene Kennzahlen', verglichen mit früheren Monaten.",
                              'fr': 'Affiché sur une diapositive « Vos chiffres », comparé aux mois précédents.'},
              'data': {'name': {'en': 'Name', 'nl': 'Naam', 'de': 'Name', 'fr': 'Nom'},
                       'statistic': {'en': 'Statistic', 'nl': 'Statistiek', 'de': 'Statistik', 'fr': 'Statistique'},
                       'type': {'en': 'Calculation', 'nl': 'Berekening', 'de': 'Berechnung', 'fr': 'Calcul'},
                       'threshold': {'en': 'Threshold (for hours or days above)',
                                     'nl': 'Drempel (voor uren of dagen boven)',
                                     'de': 'Schwelle (für Stunden oder Tage über)',
                                     'fr': 'Seuil (pour heures ou jours au-dessus)'},
                       'unit': {'en': 'Unit', 'nl': 'Eenheid', 'de': 'Einheit', 'fr': 'Unité'},
                       'decimals': {'en': 'Decimals',
                                    'nl': 'Decimalen',
                                    'de': 'Nachkommastellen',
                                    'fr': 'Décimales'}}},
 'tile_remove': {'title': {'en': 'Remove your own figures',
                           'nl': 'Eigen cijfers verwijderen',
                           'de': 'Eigene Kennzahlen entfernen',
                           'fr': 'Supprimer des chiffres'},
                 'data': {'tiles': {'en': 'Figures to remove',
                                    'nl': 'Te verwijderen cijfers',
                                    'de': 'Zu entfernende Kennzahlen',
                                    'fr': 'Chiffres à supprimer'}}}}

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


# ---- additions in 0.3 -------------------------------------------------------------------------------------------
_cl = STEPS["settings"]["sections"]["climate"]
_cl["data"]["rain_sensor"] = t("Rain gauge", "Regenmeter", "Regenmesser", "Pluviomètre")
_cl["data_description"]["rain_sensor"] = t(
    "Optional. A precipitation sensor that counts up (total); replaces the modelled rainfall.",
    "Optioneel. Een neerslagsensor die optelt (totaal); vervangt de neerslag uit het model.",
    "Optional. Ein aufsummierender Niederschlagssensor; ersetzt den modellierten Niederschlag.",
    "Facultatif. Un capteur de précipitations cumulées ; remplace la pluie modélisée.")
_car = STEPS["settings"]["sections"]["car"]
_car["data"]["evcc_url"] = t("evcc URL", "evcc-URL", "evcc-URL", "URL d'evcc")
_car.setdefault("data_description", {})["evcc_url"] = t(
    "Optional, e.g. http://192.168.1.10:7070. Adds charging sessions, cost and solar share per vehicle.",
    "Optioneel, bijv. http://192.168.1.10:7070. Voegt laadsessies, kosten en zonne-aandeel per auto toe.",
    "Optional, z. B. http://192.168.1.10:7070. Ergänzt Ladevorgänge, Kosten und Solaranteil pro Fahrzeug.",
    "Facultatif, p. ex. http://192.168.1.10:7070. Ajoute les sessions de recharge, le coût et la part solaire par véhicule.")
_car["description"] = t(
    "Any car: choose its odometer (from the car's own integration) and your charger's energy sensor. Richer sources, "
    "used first when filled in: TeslaMate (trips, Wh/km; Grafana URL and a token of a Viewer service account) and evcc "
    "(charging sessions, cost, solar share).",
    "Elke auto: kies de kilometerteller (uit de integratie van je auto) en de energiesensor van je laadpaal. Rijkere "
    "bronnen gaan voor als ze zijn ingevuld: TeslaMate (ritten, Wh/km; Grafana-URL en token van een Viewer-serviceaccount) "
    "en evcc (laadsessies, kosten, zonne-aandeel).",
    "Jedes Auto: Kilometerzähler (aus der Integration des Autos) und Energiesensor der Ladestation wählen. Reichere "
    "Quellen haben Vorrang: TeslaMate (Fahrten, Wh/km; Grafana-URL und Token eines Viewer-Dienstkontos) und evcc "
    "(Ladevorgänge, Kosten, Solaranteil).",
    "Toute voiture : compteur kilométrique (intégration de la voiture) et capteur d'énergie de la borne. Sources plus "
    "riches, prioritaires si renseignées : TeslaMate (trajets, Wh/km ; URL de Grafana et jeton Viewer) et evcc "
    "(sessions, coût, part solaire).")


_cl["data_description"]["use_open_meteo"] = t(
    "Free weather archive for your area (location rounded to ~10 km). Off: only your own sensors, without normals or sunshine.",
    "Gratis weerarchief voor jouw omgeving (locatie afgerond op ~10 km). Uit: alleen je eigen sensoren, zonder normalen of zon.",
    "Kostenloses Wetterarchiv für Ihre Gegend (Standort auf ~10 km gerundet). Aus: nur Ihre eigenen Sensoren, ohne Normalwerte und Sonne.",
    "Archive météo gratuite pour votre région (position arrondie à ~10 km). Désactivé : seulement vos capteurs, sans normales ni soleil.")


_tile = STEPS["tile_add"]
_tile["data"]["run_hours"] = t("Typical length of one run", "Typische duur van één beurt", "Typische Dauer eines Durchgangs", "Durée typique d'un cycle")
_tile.setdefault("data_description", {})["run_hours"] = t(
    "For runs only, optional: a longer block counts as several runs (e.g. 3 h for a dishwasher). Runs are counted from the hourly average power; pauses of up to 2 hours belong to the same run.",
    "Alleen voor beurten, optioneel: een langer blok telt als meerdere beurten (bijv. 3 uur voor een vaatwasser). Beurten worden geteld uit het uurgemiddelde vermogen; pauzes tot 2 uur horen bij dezelfde beurt.",
    "Nur für Durchgänge, optional: ein längerer Block zählt als mehrere Durchgänge (z. B. 3 h für einen Geschirrspüler). Gezählt wird aus der stündlichen Durchschnittsleistung; Pausen bis 2 Stunden gehören zum selben Durchgang.",
    "Pour les cycles uniquement, facultatif : un bloc plus long compte comme plusieurs cycles (p. ex. 3 h pour un lave-vaisselle). Les cycles sont comptés à partir de la puissance moyenne horaire ; les pauses jusqu'à 2 heures font partie du même cycle.")


STEPS["settings"]["sections"]["general"]["data"]["admin_only"] = t(
    "Only administrators can view the reports", "Alleen beheerders mogen de rapporten zien",
    "Nur Administratoren dürfen die Berichte sehen", "Seuls les administrateurs peuvent voir les rapports")
STEPS["settings"]["sections"]["general"]["data_description"]["admin_only"] = t(
    "Off: every Home Assistant user in the household can open them (they show energy use, costs and when rooms are used).",
    "Uit: elke Home Assistant-gebruiker in huis kan ze openen (ze tonen energieverbruik, kosten en wanneer ruimtes gebruikt worden).",
    "Aus: jeder Home-Assistant-Benutzer im Haushalt kann sie öffnen (sie zeigen Energieverbrauch, Kosten und Raumnutzung).",
    "Désactivé : tout utilisateur de Home Assistant du foyer peut les ouvrir (ils montrent consommation, coûts et usage des pièces).")
_en = STEPS["settings"]["sections"]["energy"]
_en["data"]["gas_base_per_day"] = t("Gas for hot water and cooking per day", "Gas voor warm water en koken per dag",
                                    "Gas für Warmwasser und Kochen pro Tag", "Gaz pour eau chaude et cuisson par jour")
_en["data_description"]["gas_base_per_day"] = t(
    "Optional, in your gas unit (e.g. 0.4 m³). Splits gas into heating and the rest. Empty: estimated per month from how gas use follows the degree days.",
    "Optioneel, in je gaseenheid (bijv. 0,4 m³). Splitst gas in verwarming en de rest. Leeg: per maand geschat uit hoe het gasverbruik de graaddagen volgt.",
    "Optional, in Ihrer Gaseinheit (z. B. 0,4 m³). Teilt Gas in Heizung und Rest. Leer: pro Monat geschätzt aus dem Verlauf gegenüber den Gradtagen.",
    "Facultatif, dans votre unité de gaz (p. ex. 0,4 m³). Sépare le gaz entre chauffage et reste. Vide : estimé chaque mois selon le lien avec les degrés-jours.")
_en["data"]["gas_use"] = t("Gas used for", "Gas gebruikt voor", "Gas verwendet für", "Gaz utilisé pour")
_en["data_description"]["gas_use"] = t(
    "Only hot water and cooking: for a home heated otherwise (e.g. a heat pump); all gas then counts as hot water and cooking. Otherwise heating and hot water are split per month from how gas follows the weather, or measured from the boiler's status below.",
    "Alleen warm water en koken: voor een huis dat anders verwarmd wordt (bijv. een warmtepomp); al het gas telt dan als warm water en koken. Anders worden verwarming en warm water per maand gescheiden uit hoe het gas het weer volgt, of gemeten uit de ketelstatus hieronder.",
    "Nur Warmwasser und Kochen: für ein anders beheiztes Haus (z. B. Wärmepumpe); alles Gas zählt dann als Warmwasser und Kochen. Sonst werden Heizung und Warmwasser pro Monat aus dem Wetterverlauf getrennt oder aus dem Kesselstatus unten gemessen.",
    "Uniquement eau chaude et cuisson : pour une maison chauffée autrement (p. ex. pompe à chaleur) ; tout le gaz compte alors comme eau chaude et cuisson. Sinon, chauffage et eau chaude sont séparés chaque mois selon le lien avec la météo, ou mesurés à partir de l'état de la chaudière ci-dessous.")
GAS_USE = {"heating_and_hot_water": t("Heating and hot water", "Verwarming en warm water", "Heizung und Warmwasser", "Chauffage et eau chaude"),
           "hot_water_only": t("Only hot water and cooking", "Alleen warm water en koken", "Nur Warmwasser und Kochen", "Uniquement eau chaude et cuisson")}
_en["data"]["gas_hot_water_active"] = t("Boiler: hot water active", "Ketel: warm water actief",
                                        "Kessel: Warmwasser aktiv", "Chaudière : eau chaude active")
_en["data_description"]["gas_hot_water_active"] = t(
    "Optional: the boiler's hot-water status (e.g. OpenTherm). With this and/or the heating status, gas is split per hour from what the boiler was doing instead of being estimated from the weather. A sensor adds up the hours; it is used once it has measured at least 7 days of a month.",
    "Optioneel: de warmwaterstatus van de ketel (bijv. OpenTherm). Hiermee en/of met de verwarmingsstatus wordt gas per uur verdeeld op basis van wat de ketel deed, in plaats van geschat uit het weer. Een sensor telt de uren op; het telt mee zodra die minstens 7 dagen van een maand heeft gemeten.",
    "Optional: der Warmwasserstatus des Kessels (z. B. OpenTherm). Damit und/oder mit dem Heizstatus wird Gas stündlich nach dem tatsächlichen Betrieb aufgeteilt statt aus dem Wetter geschätzt. Ein Sensor summiert die Stunden; er wird verwendet, sobald er mindestens 7 Tage eines Monats gemessen hat.",
    "Facultatif : l'état eau chaude de la chaudière (p. ex. OpenTherm). Avec celui-ci et/ou l'état chauffage, le gaz est réparti heure par heure selon ce que faisait la chaudière, au lieu d'être estimé d'après la météo. Un capteur additionne les heures ; il est utilisé dès qu'il a mesuré au moins 7 jours d'un mois.")
_en["data"]["gas_heating_active"] = t("Boiler: heating active", "Ketel: verwarming actief",
                                      "Kessel: Heizung aktiv", "Chaudière : chauffage actif")
_en["data_description"]["gas_heating_active"] = t(
    "Optional: the boiler's central-heating status (binary sensor), or a thermostat (counts as heating while it reports heating).",
    "Optioneel: de cv-status van de ketel (binary sensor), of een thermostaat (telt als verwarming zolang die 'verwarmen' meldt).",
    "Optional: der Heizstatus des Kessels (Binärsensor) oder ein Thermostat (zählt als Heizen, solange es „heizt“ meldet).",
    "Facultatif : l'état chauffage de la chaudière (capteur binaire), ou un thermostat (compte comme chauffage tant qu'il indique « chauffe »).")
ENTITY = {"hot_water_time": t("Boiler hot water on-time", "Ketel warm water aan-tijd", "Kessel Warmwasser-Laufzeit",
                              "Durée eau chaude chaudière"),
          "heating_time": t("Boiler heating on-time", "Ketel verwarming aan-tijd", "Kessel Heizungs-Laufzeit",
                            "Durée chauffage chaudière")}
CONFIG["user"]["data_description"]["backfill_months"] = t(
    "Earlier months are generated in the background from long-term statistics. The suggestion covers all of last year and this year so far, so both year reviews start complete. Use 0 to skip.",
    "Eerdere maanden worden op de achtergrond gemaakt uit de langetermijnstatistieken. Het voorstel dekt heel vorig jaar en dit jaar tot nu toe, zodat beide jaaroverzichten compleet beginnen. Gebruik 0 om over te slaan.",
    "Frühere Monate werden im Hintergrund aus Langzeitstatistiken erstellt. Der Vorschlag umfasst das ganze letzte Jahr und dieses Jahr bisher, damit beide Jahresrückblicke vollständig sind. 0 zum Überspringen.",
    "Les mois précédents sont générés en arrière-plan. La suggestion couvre toute l'année dernière et cette année jusqu'ici, pour que les deux bilans annuels soient complets. 0 pour ignorer.")
SERVICES["backfill"]["fields"]["months"] = (t("Months", "Maanden", "Monate", "Mois"), t(
    "How many months to look back. Default: back to the start of last year (in your year review's months).",
    "Hoeveel maanden terug. Standaard: tot het begin van vorig jaar (volgens de startmaand van je jaaroverzicht).",
    "Wie viele Monate zurück. Standard: bis zum Beginn des letzten Jahres (gemäß Startmonat des Jahresrückblicks).",
    "Combien de mois en arrière. Par défaut : jusqu'au début de l'année dernière (selon le mois de début du bilan annuel)."))
_gen = STEPS["settings"]["sections"]["general"]
_gen["data"]["default_theme"] = t("Default theme", "Standaardthema", "Standarddesign", "Thème par défaut")
_gen["data_description"]["default_theme"] = t(
    "Used until a viewer picks another theme at the end of a report (remembered per browser).",
    "Geldt tot iemand onderaan een rapport een ander thema kiest (dat wordt per browser onthouden).",
    "Gilt, bis jemand am Ende eines Berichts ein anderes Design wählt (pro Browser gespeichert).",
    "Utilisé jusqu'à ce qu'un lecteur choisisse un autre thème en fin de rapport (mémorisé par navigateur).")
THEME_NAMES = {
    "auto": t("Automatic (follows light/dark)", "Automatisch (volgt licht/donker)", "Automatisch (hell/dunkel)", "Automatique (clair/sombre)"),
    "light": t("Light", "Licht", "Hell", "Clair"),
    "dark": t("Dark", "Donker", "Dunkel", "Sombre"),
    "night": t("Night", "Nacht", "Nacht", "Nuit"),
    "mono": t("Black and white", "Zwart-wit", "Schwarz-weiß", "Noir et blanc"),
    "ha": t("Home Assistant (follows your Home Assistant theme)", "Home Assistant (volgt je Home Assistant-thema)",
            "Home Assistant (folgt Ihrem Home-Assistant-Design)", "Home Assistant (suit votre thème Home Assistant)"),
}
_en["data_description"]["fixed_costs_daily"] = t(
    "Optional, including tax: standing charges and grid fees minus a fixed daily tax credit (may be negative).",
    "Optioneel, inclusief btw: vaste leveringskosten en netbeheer min een vaste korting per dag (mag negatief zijn).",
    "Optional, inkl. Steuern: Grundgebühr und Netzentgelte abzüglich einer festen Gutschrift pro Tag (darf negativ sein).",
    "Facultatif, TTC : abonnement et frais de réseau moins une remise fixe par jour (peut être négatif).")
_cl["data"]["degree_day_base"] = t("Heating threshold for degree days", "Stookgrens voor graaddagen",
                                   "Heizgrenze für Gradtage", "Seuil de chauffage des degrés-jours")
_cl["data_description"]["degree_day_base"] = t(
    "Optional. Days with an average temperature below this count as heating days. Empty: 18 °C (65 °F). To compare with another service, use the same value it uses.",
    "Optioneel. Dagen met een gemiddelde temperatuur onder deze waarde tellen als stookdag. Leeg: 18 °C. Vergelijk je met een andere dienst, gebruik dan dezelfde waarde als die dienst.",
    "Optional. Tage kälter als dieser Wert zählen als Heiztage. Leer: 18 °C (65 °F).",
    "Facultatif. Les jours plus froids comptent comme jours de chauffe. Vide : 18 °C (65 °F).")
_cl["data"]["degree_days_weighted"] = t("Weighted degree days (Dutch method)", "Gewogen graaddagen (Nederlandse methode)",
                                        "Gewichtete Gradtage (niederländische Methode)", "Degrés-jours pondérés (méthode néerlandaise)")
_cl["data_description"]["degree_days_weighted"] = t(
    "November to February count ×1.1, March and October ×1.0, April to September ×0.8: the weighting commonly used in the Netherlands to compare gas use. Earlier months are updated automatically.",
    "November t/m februari tellen ×1,1, maart en oktober ×1,0, april t/m september ×0,8: de weging die in Nederland gebruikelijk is om gasverbruik te vergelijken. Eerdere maanden worden automatisch bijgewerkt.",
    "November bis Februar zählen ×1,1, März und Oktober ×1,0, April bis September ×0,8. Frühere Monate werden automatisch aktualisiert.",
    "Novembre à février ×1,1, mars et octobre ×1,0, avril à septembre ×0,8. Les mois précédents sont mis à jour automatiquement.")
ERRORS = {
    "statistic_required": t("Choose a statistic.", "Kies een statistiek.", "Wählen Sie eine Statistik.", "Choisissez une statistique."),
    "invalid_url": t("Enter a valid http:// or https:// address without query or fragment.",
                     "Vul een geldig http://- of https://-adres in, zonder ? of #.",
                     "Geben Sie eine gültige http://- oder https://-Adresse ohne ? oder # ein.",
                     "Saisissez une adresse http:// ou https:// valide, sans ? ni #."),
    "url_credentials": t("Don't put a user name or password in the address; use the token field.",
                         "Zet geen gebruikersnaam of wachtwoord in het adres; gebruik het tokenveld.",
                         "Keine Benutzernamen oder Passwörter in die Adresse; nutzen Sie das Token-Feld.",
                         "Pas de nom d'utilisateur ni de mot de passe dans l'adresse ; utilisez le champ du jeton."),
    "https_required": t("The token would be sent unencrypted to an address outside your network; use https://.",
                        "De token zou onversleuteld naar een adres buiten je netwerk gaan; gebruik https://.",
                        "Das Token würde unverschlüsselt an eine Adresse außerhalb Ihres Netzes gehen; nutzen Sie https://.",
                        "Le jeton serait envoyé en clair vers une adresse hors de votre réseau ; utilisez https://."),
    "teslamate_incomplete": t("Fill in both the Grafana address and the token, or neither.",
                              "Vul zowel het Grafana-adres als de token in, of geen van beide.",
                              "Füllen Sie Grafana-Adresse und Token beide aus oder keines von beiden.",
                              "Renseignez l'adresse Grafana et le jeton, ou aucun des deux."),
    "too_long": t("At most 1000 characters.", "Hooguit 1000 tekens.", "Höchstens 1000 Zeichen.", "1000 caractères au maximum."),
}


def _strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, str):
        yield node


def pick(node, lang):
    if isinstance(node, dict) and set(node) == set(LANGS):
        return node[lang]
    if isinstance(node, dict):
        return {k: pick(v, lang) for k, v in node.items()}
    return node


from translations_extra import EXTRA  # noqa: E402  (es/it: English text -> translation)


def localize(node, table):
    if isinstance(node, dict):
        return {k: localize(v, table) for k, v in node.items()}
    if isinstance(node, str):
        return table.get(node, node)
    return node


for lang in LANGS:
    steps = {k: pick(v, lang) for k, v in STEPS.items()}
    doc = {
        "config": {"abort": pick(CONFIG["abort"], lang), "step": {"user": pick(CONFIG["user"], lang)}},
        "options": {"step": steps, "error": {k: v[lang] for k, v in ERRORS.items()}},
        "selector": {
            "month": {"options": {str(i + 1): m for i, m in enumerate(MONTHS[lang])}},
            "tile_type": {"options": {k: v[lang] for k, v in TILE.items()}},
            "theme": {"options": {k: v[lang] for k, v in THEME_NAMES.items()}},
            "gas_use": {"options": {k: v[lang] for k, v in GAS_USE.items()}},
        },
        "entity": {"sensor": {k: {"name": v[lang]} for k, v in ENTITY.items()}},
        "services": {k: {"name": v["name"][lang], "description": v["description"][lang],
                         "fields": {f: {"name": n[lang], "description": d[lang]} for f, (n, d) in v["fields"].items()}}
                     for k, v in SERVICES.items()},
    }
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    (OUT / "translations" / f"{lang}.json").write_text(text, encoding="utf-8")
    if lang == "en":
        (OUT / "strings.json").write_text(text, encoding="utf-8")
en_doc = json.loads((OUT / "translations" / "en.json").read_text(encoding="utf-8"))
for lang, table in EXTRA.items():
    missing = sorted({x for x in _strings(en_doc) if x not in table and x != "Home in Review"})
    if missing:
        print(f"{lang}: {len(missing)} untranslated:", missing[:5])
    (OUT / "translations" / f"{lang}.json").write_text(
        json.dumps(localize(en_doc, table), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("written", ", ".join([*LANGS, *EXTRA]))
