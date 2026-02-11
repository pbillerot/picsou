# CHANGELOG

Historique des modifications

### À venir :
-

5.0.3 du 11 fev. 2026
------------------------
- test panda

5.0.2 du 7 mai 2025
------------------------
- Correction bug calcul rsi si down est à 0

5.0.1 du 18 mars 2025
------------------------
- Correction bug yfinance - trop de requêtes simultanées - passage version 0.2.54

5.0.0 du 11 sept 2024
------------------------
- Suite API finance v1 yahoo, utilisation du module yfinance

4.6.3 du 9 août 2023
------------------------
- `added` suite commentaire multiligne suppression crlf dans le png

4.6.2 du 28 juillet 2023
------------------------
- `fixed` histo sur valeur disabled

4.6.1 du 27 juillet 2023
------------------------
- `fixed` calcul rsi et 3.5% mainetent sur close et non pas sur open

4.6.0 du 27 juillet 2023
------------------------
- `changed` histo dans table HISTO au lieu de QUOTESNEW

4.5.0 du 25 juillet 2023
------------------------
- `added` -histo <valeur>

4.4.0 du 25 juillet 2023
------------------------
- `added` aide MdWiki dans répertoire wiki
- `changed` répertoire chandelier remplacé par wiki

4.3.2 du 19 juillet 2023
------------------------
- `fixed` augmentation varchar des candles

4.3.1 du 19 juillet 2023
------------------------
- `fixed` correction import quote à zéro

4.3.0 du 19 juillet 2023
------------------------
- `removed` suppression tables histo et histonew
- `changed` load cours dans quotesnew puis fusion QUOTES

4.2.0 du 19 juillet 2023
------------------------
- `added` erreur avec n° ligne du source
- `changed` load histo et quotes dans table HISTONEW et QUOTESNEW puis fusion dans HIST et QUOTES

4.1.4 du 17 juillet 2023
------------------------
- `changed` bougies sansFlyiers

4.1.3 du 17 juillet 2023
------------------------
- `fixed` correction des chandeliers

4.1.2 du 16 juillet 2023
------------------------
- `fixed` plot remplacé par scatter pour les seuils si une seule journée d'achat

4.1.1 du 16 juillet 2023
------------------------
- `added` ajout trend dans graph histo

4.1.0 du 16 juillet 2023
------------------------
- `added` ajout calcul du trend = mme100 - mme100-14j en %

4.0.4 du 15 juillet 2023
------------------------
- `fixed` csv histo su pg et non pas sur sqlite

4.0.3 du 15 juillet 2023
------------------------
- `changed` ajout apdate ptf_rsi à partir de quotes

4.0.2 du 13 juillet 2023
------------------------
- `changed` optimisation des calculs et du stockage dans les tables - pas de redondance

4.0.1 du 13 juillet 2023
------------------------
- `added` Version pour postgres exclusivement

3.4.1 du 11 juillet 2023
----------------------
- `fixed` correction paramètres sqlite

3.4.0 du 11 juillet 2023
----------------------
- `added` génération historique 1 an des valeurs stockées dans pase picsou postgres

3.3.4 du 7 juillet 2023
----------------------
- `changed` barre rentabilité en vente seulement à partir de la date d'achat

3.3.3 du 5 juillet 2023
----------------------
- `fixed` décalage des couleurs des bougies

3.3.2 du 5 juillet 2023
----------------------
- `fixed` correction des 3 corbeaux rouges

3.3.1 du 5 juillet 2023
----------------------
- `added` title avec rsi et macd

3.3.0 du 5 juillet 2023
----------------------
- `added` candle rsi macd sur le même graphique

3.2.1 du 4 juillet 2023
----------------------
- `fixed` chemin d'accès à picsou.json

3.2.0 du 4 juillet 2023
----------------------
- `added` graph quotes avec candle rsi mme12 mme26

3.1.0 du 3 juillet 2023
----------------------
- `added` graph quotes avec candle et rsi

3.0.2 du 3 juillet 2023
----------------------
- `changed` graph stablae avant candle

3.0.1 du 2 juillet 2023
----------------------
- `added` début graphique avec candle

3.0.0 du 1er juillet 2023
----------------------
- `added` rsi dans table quotes

2.1.0 du 30 juin 2023
----------------------
- `changed` histo candle0 1 2 dans ptf

2.0.2 du 29 juin 2023
----------------------
- `fixed` poussée baissière haussière ctrl 50%

2.0.1 du 29 juin 2023
----------------------
- `added` analyse des chandeliers

1.3.1 du 8 février 2023
----------------------
- `added` image analyse issue de boursier.com
- `changed` image historique issue de boursier.com

1.3.0 du 5 février 2023
----------------------
- `changed` image analyse issue de boursier.com au lieu des echos obsolète

1.2.3 du 22 juillet 2021
----------------------
- `changed` affichage debug load logger enlevé

1.2.2 du 22 juillet 2021
----------------------
- `fixed` arrêt utilisation de cdays

1.2.1 du 22 juillet 2021
----------------------
- `fixed` logger non initialisé

1.2.0 du 19 juillet 2021
----------------------
- `added` docker timezone Europe/Paris
- `added` docker crontab oks
- `added` docker entrypoint.sh

1.1.0 du 19 juillet 2021
----------------------
- `added` installation de picsou dans un container docker

1.0.2 du 18 juillet 2021
----------------------
- `changed` nettoyage config.json

1.0.1 du 18 juillet 2021
----------------------
- `added` readme avec images

1.0.0 du 18 juillet 2021
----------------------
- `fixed` picsou -h -quotes -graph

0.2.0 du 17 juillet 2021
----------------------
- `fixed` picsou -h

0.1.0 du 17 juillet 2021
----------------------
- `added` picsou batch isolé du projet crudenome

###### Types de changements:
- `added` *pour les nouvelles fonctionnalités.*
- `changed` *pour les changements aux fonctionnalités préexistantes.*
- `deprecated` *pour les fonctionnalités qui seront bientôt supprimées*.
- `removed` *pour les fonctionnalités désormais supprimées.*
- `fixed` *pour les corrections de bugs.*
- `security` *en cas de vulnérabilités.*
