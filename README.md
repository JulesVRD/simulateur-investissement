# Simulateur d'investissement

Application Streamlit qui simule un investissement à intérêts composés : capital de départ, versements mensuels,
intérêts, frais, inflation et fiscalité (PEA et compte-titres). Le graphique principal empile trois couches dont la
somme est le capital total : le capital de départ, les versements cumulés et les intérêts.

## Fonctionnalités

- Versement mensuel fixe, avec hausse annuelle optionnelle, ou pourcentage du salaire.
- Salaire qui évolue selon trois trajectoires de carrière : peu favorable, moyenne, très favorable.
- Frais annuels, inflation et affichage en euros constants.
- Fiscalité à la sortie : PEA (avec plafond de versements, le surplus étant placé sur un compte-titres) et
  compte-titres, avec comparatif des deux.
- Objectif inversé : pour atteindre un capital donné, calcul du versement mensuel (ou de la part du salaire), de la
  durée ou du rendement nécessaire.
- Comparaison de plusieurs scénarios.
- Sauvegarde et réouverture des scénarios, export CSV du tableau annuel.

## Installation

Python 3.10 ou supérieur (testé avec Python 3.14).

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'application est servie sur http://localhost:8501.

## Utilisation

L'application comporte quatre onglets.

- Simulation : graphique, indicateurs, comparatif PEA / compte-titres, tableau année par année.
- Salaire et épargne : disponible avec le mode de versement « % de mon salaire ». Affiche les trois trajectoires
  de salaire et leur effet sur le capital.
- Objectif inversé : calcule ce qu'il faut pour atteindre un capital visé, brut ou net d'impôt.
- Comparaison de scénarios : jusqu'à six scénarios côte à côte.

Les paramètres sont dans le panneau de gauche. Un scénario est l'ensemble des paramètres sous un nom : il est
enregistré dans `scenarios/<nom>.json` et peut être rouvert, exporté ou importé depuis le même panneau.
Quelques scénarios d'exemple sont fournis dans `scenarios/`.

## Modèle de calcul

Le calcul est effectué mois par mois (`simulator/engine.py`).

```
croissance mensuelle = (1 + rendement annuel)^(1/12) * (1 - frais annuels)^(1/12)
capital[t]           = capital[t-1] * croissance mensuelle + versement[t]
intérêts[t]          = capital[t] - capital de départ - somme des versements
```

- Le versement est effectué en fin de mois. En mode fixe, il augmente à chaque anniversaire de la hausse annuelle
  choisie. En mode salaire, il vaut la part choisie multipliée par le salaire net du mois.
- Euros constants : le montant du mois t est divisé par (1 + inflation)^(t/12).
- Objectif inversé : recherche par dichotomie du versement, de la part du salaire ou du rendement, et premier mois
  atteignant l'objectif pour la durée. Le solveur utilise le même moteur que la simulation.

### Fiscalité

L'impôt est calculé sur la plus-value (valeur moins versements), comme si le portefeuille était intégralement
retiré à la date considérée. Taux 2026, modifiables dans l'application :

- compte-titres : 12,8 % d'impôt sur le revenu et 18,6 % de prélèvements sociaux, soit 31,4 % ;
- PEA détenu depuis cinq ans ou plus : 18,6 % ; avant cinq ans : 31,4 %.

Le PEA est plafonné à 150 000 euros de versements cumulés, capital de départ compris. Une fois le plafond atteint,
les versements suivants sont placés sur un compte-titres. Chaque compte est taxé selon sa propre règle.

### Salaire

Le salaire net mensuel augmente une fois par an. Le taux d'augmentation dépend de la phase de carrière (années 1 à
5, 6 à 15, 16 et suivantes). Les profils proposés (ingénieur, master, licence professionnelle ou BUT, autre) donnent
un salaire de départ et trois jeux d'augmentations. Ces valeurs sont indicatives et modifiables.

Le profil ingénieur s'appuie sur l'enquête d'insertion de l'UTT (promotion 2024), l'enquête d'insertion de la CGE
2025 et les salaires médians par âge de l'enquête IESF 2025. Les profils master et licence professionnelle s'appuient
sur les enquêtes d'insertion du ministère de l'Enseignement supérieur (SIES) pour le salaire de départ ; leur
progression est extrapolée.

## Hypothèses et limites

- Rendement régulier : pas de volatilité ni de simulation Monte-Carlo.
- Versements en fin de mois, capitalisation mensuelle.
- Taux de frais, d'inflation et d'imposition constants sur toute la durée.
- Fiscalité simplifiée : sortie totale, pas de compensation de moins-values, pas d'impôt sur les dividendes en cours
  de route, pas de frais de courtage.
- PEA supposé ouvert au début de la simulation, avec les mêmes rendement et frais que le compte-titres. Seul le PEA
  classique est modélisé.
- Salaire : net avant impôt sur le revenu, hors primes variables, sans interruption de carrière. Les enquêtes ne
  distinguent pas les spécialités.

## Structure

```
app.py                  Point d'entrée Streamlit
simulator/              Calcul, sans dépendance à Streamlit
  params.py             Paramètres, bornes et validation
  engine.py             Calcul mois par mois
  salary_profiles.py    Profils de salaire et trajectoires
  salary.py             Trajectoire du salaire, calendrier des versements
  taxes.py              Fiscalité PEA / compte-titres
  metrics.py            Indicateurs, tableau annuel
  solver.py             Objectif inversé
  storage.py            Sauvegarde et chargement des scénarios (JSON)
  charts.py             Graphiques Plotly
  export.py             Export CSV
  formatting.py         Mise en forme des montants et durées
ui/                     Interface Streamlit, un module par zone
scenarios/              Scénarios enregistrés
```

## Avertissement

Simulation pédagogique fondée sur des hypothèses. Ce n'est ni une prévision, ni une garantie de rendement, ni un
conseil en investissement.
