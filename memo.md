# ABC Technique

## Préalable
- mkdir log

## Installation du Virtualenv
```shell
sudo apt install virtualenv
virtualenv --python=/usr/bin/python3 venv

dans vscodium crtl+shift+P Venv

source venv/bin/activate

pip3 install matplotlib requests psycopg[binary] yfinance

dans vscodium crtl+shift+P Venv

```
### Pour VSCodium
- Installer l'extension ```ms-python.python```
- Installer pylint pour python ```pip3 install pylint rope```

## SQL
- Utilisation de DB Browser for SQLite http://sqlitebrowser.org/
- sudo apt install sqlitebrowser
- Création des tables SQLite

## Démarche

## Dessins
https://drive.google.com/open?id=1v-FKCZdRNJAXW89Xy-yA2kBaMQPxnXQT

## docker
docker exec -it beethon /bin/bash

## Connexion postgresql sur un VPS en SSH
ssh -L 5432:ionos.billerot.net:5432 debian@ionos.billerot.net

## API yfinance
- https://github.com/ranaroussi/yfinance
- https://datatofish.com/pandas-dataframe-to-sql/
