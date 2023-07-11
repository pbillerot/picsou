# -*- coding:Utf-8 -*-
"""
    Fonctions utiles regroupées dans une classe
"""
from email.mime.text import MIMEText
import os
import json
from collections import OrderedDict
import re
import smtplib
import importlib
# pip install requets
import requests

# https://www.psycopg.org/psycopg3/docs/basic/usage.html
# pip install "psycopg[binary]"
import psycopg
import sqlite3

class Crud:
    """
    Fonctions utiles regroupées dans une classe
    """
    # connecteurs aux base de données
    sqlite = None
    pg = None
    # fusion de config.json et local.json
    config = {}

    def __init__(self, args):
        """ Initialisation """

        """
        Chargement des json config.json et local.json
        """
        self.args = args

        dir_path = os.path.dirname(os.path.realpath(__file__))
        # chargement de config.json et local.json
        os.chdir(dir_path)
        with open("config.json") as json_data_file:
            self.config = json.load(json_data_file)
        with open("local.json") as json_data_file:
            self.config.update(json.load(json_data_file))

        if self.args.test :
            print(json.dumps(self.config))

    #
    # FONCTIONS GENERALES
    #
    def send_sms(self, msg):
        """ envoi d'un sms """
        try:
            result = requests.get(self.config["sms"] % requests.utils.quote(msg))
        except Exception as ex:
            print(getattr(ex, 'message', repr(ex)))

    def get_json_content(self, path):
        """
        Retourne le contenu d'un fichier json dans un dictionnaire
        """
        store = {}
        try:
            with open(path) as json_data_file:
                store = json.load(json_data_file, object_pairs_hook=OrderedDict)
        except Exception as ex:
            print(getattr(ex, 'message', repr(ex)))
        return store

    def get_resource_path(self, rel_path):
        dir_of_py_file = os.path.dirname(__file__)
        rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
        abs_path_to_resource = os.path.abspath(rel_path_to_resource)
        return os.path.expanduser(abs_path_to_resource)

    def exec_sql(self, sqlite_or_pg, sql, params):
        """
        Exécution d'un ordre sql
        """
        conn = self.open_sqlite() if sqlite_or_pg == "sqlite" else self.open_pg()
        try:
            cursor = conn.cursor()
            pp = {}
            for param in params:
                if params[param] is None or isinstance(params[param], int) or isinstance(params[param], float):
                    pp[param] = params[param]
                else:
                    pp[param] = params[param]
            cursor.execute(sql, pp)
            conn.commit()
        except BaseException as e:
            print("Error %s %s %s".format(e, sql, params))
            conn.rollback()
        else:
            conn.commit()
        finally:
            conn.close()

    def sql_to_dict(self, sqlite_or_pg, sql, params, source=""):
        """
        Chargement du résultat d'une requête sql dans dictionnaire
        """
        conn = self.open_sqlite() if sqlite_or_pg == "sqlite" else self.open_pg()
        data = None
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            desc = cursor.description
            column_names = [col[0] for col in desc]
            data = [OrderedDict(zip(column_names, row)) for row in cursor]
        except BaseException as e:
            print("Error {} {} {}".format(e, sql, params))
            conn.rollback()
        else:
            conn.commit()
        finally:
            conn.close()
        return data

    def get_sql(self, sqlite_or_pg, sql):
        """
        Requête sql pour lire une donnée dans la table
        """
        conn = self.open_sqlite() if sqlite_or_pg == "sqlite" else self.open_pg()
        data = ""
        try:
            cursor = conn.cursor()
            for row in cursor.execute(sql):
                data = row[0]
        except BaseException as e:
            print("Error %s %s %s".format(e, sql, params))
            conn.rollback()
        else:
            conn.commit()
        finally:
            conn.close()
        return data

    def get_params_display(self, params):
        """ formattage pour l'affichage des paramètres transmis à une requete sql """
        fmt = ""
        for key in params:
            if params[key] is None:
                continue
            # if isinstance(params[key], (str, int, float)):
            if fmt != "":
                fmt += ", "
            fmt += "%s='%s'" % (key, str(params[key]))
        return "params: [%s]" % fmt

    def send_mail(self, dests, subject, body):
        """
        Envoyer un mail
        """
        from_addr = self.config["smtp_from"]

        mail = MIMEText(body, "html", "utf-8")
        mail['From'] = from_addr
        mail['Subject'] = subject

        smtp = smtplib.SMTP()
        smtp.connect(self.config["smtp_host"])
        for _i in dests:
            smtp.sendmail(from_addr, _i, mail.as_string())
            print("Mail to %s %s".format(_i, subject))

        smtp.close()

    def directory_list(self, path):
        """
        Liste des fichiers d'un répertoire
        """
        file_list = []
        try:
            for filename in os.listdir(path):
                file_list.append(filename)
        except BaseException as ex:
            print(getattr(ex, 'message', repr(ex)))
        return file_list

    def get_key_from_bracket(self, text):
        """ Retourne la clé entre parenthèses
        "Label bla bla (key)" va retourner "key"
        """
        res = re.search('.*\((.*)\).*', text)
        if res:
            return res.group(1)
        else:
            return text

    def load_class(self, full_class_string):
        """
        dynamically load a class from a string
        """
        class_data = full_class_string.split(".")
        module_path = ".".join(class_data[:-1])
        class_str = class_data[-1]

        module = importlib.import_module(module_path)
        # Finally, we retrieve the Class
        return getattr(module, class_str)

    def open_sqlite(self):
        """ sqlite or postgres """
        # if self.sqlite is None:
        self.sqlite = sqlite3.connect(self.get_config("sqlite"))

        return self.sqlite

    def open_pg(self):
        """ sqlite or postgres """
        # if self.pg is None:
        chaine_connection = "user={} password={} dbname={} host={} port={}".format(self.get_config("pg_user"),self.get_config("pg_password"),self.get_config("pg_dbname"),self.get_config("pg_host"),self.get_config("pg_port"))
        self.pg = psycopg.connect(chaine_connection)
        return self.pg

    def get_config(self, param):
        return self.config.get(param)