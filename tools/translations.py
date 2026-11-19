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
                       'threshold': {'en': 'Threshold (for hours above)',
                                     'nl': 'Drempel (voor uren boven)',
                                     'de': 'Schwelle (für Stunden über)',
                                     'fr': 'Seuil (pour heures au-dessus)'},
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
        "options": {"step": steps, "error": {"statistic_required": t(
            "Choose a statistic.", "Kies een statistiek.", "Wählen Sie eine Statistik.", "Choisissez une statistique.")[lang]}},
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
