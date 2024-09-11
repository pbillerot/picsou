#./venv/bin/python3
# -*- coding:Utf-8 -*-
"""
    Batch de mise à jour des données de la base picsou
"""
import shutil
import os
import datetime, time, locale
import argparse
import sys
import glob
import re
import random
import decimal
import traceback
import re
import urllib.request

# pip install yfinance
import yfinance as yf

# pip install requets
import requests
# pip install matplotlib
# import matplotlib.pyplot as plt
# csv
from contextlib import closing
import csv
from codecs import iterdecode

# from crud import Crud
# from cpu import Cpu

class Picsou():
    """ Actualisation des cours """

    def histo(self, quote_id):
        """
            Pour intégrer une nouvelle valeur
        """
        conn = self.crud.open_pg()
        try:
            ptfs = self.crud.sql_to_dict("pg", """
            SELECT * FROM ptf where ptf_id = %s
            ORDER BY ptf_id
            """, [quote_id])
            # Partage du header et du cookie entre toutes les requêtes
            header, crumb, cookies = self.cpu.get_crumbs_and_cookies('ACA.PA')

            # Suppression des records de HISTONEW
            cursor = conn.cursor()
            cursor.execute("DELETE FROM HISTO", [])
            conn.commit()

            self.pout("Load Histo of")
            qlast = self.crud.get_config("qlast_quotes")
            for ptf in ptfs:
                self.pout(" {}".format(ptf["ptf_id"]))
                # Chargement de l'historique
                # remplissage de la table quotes - dernière quote dans self.quote
                self.histo_load(ptf, 500, header, cookies)
            self.display("")
            cursor.execute("""
            insert into QUOTES select * from HISTO ON CONFLICT DO NOTHING
            """, {})
            conn.commit()
        except BaseException as e:
            print(traceback.format_exc())
            conn.rollback()
            conn.close()
            exit(1)
        else:
            conn.commit()
        finally:
            conn.close()

        self.display("")

    def histo_load(self, ptf, nbj, header, cookies):
        """
        Récupération de l'historique des cours des actions
        """
        # end_date = int(time.mktime(datetime.datetime.now().timetuple()))
        end_date = int(time.time())
        start_date = int(time.mktime((datetime.datetime.now() - datetime.timedelta(days=nbj)).timetuple()))

        url = "https://query1.finance.yahoo.com/v7/finance/download/{}?period1={}&period2={}&interval=1d&events=history"\
        .format(ptf["ptf_id"], start_date, end_date)
        # self.display(url)
        with requests.Session() as req:
            conn = self.crud.open_pg()
            try:
                res = req.get(url, headers=header, cookies=cookies)
                for block in res.iter_content(256):
                    if b'error' in block:
                        raise ValueError("ERREUR yahoo %s" % block)

                if res.encoding is None:
                    res.encoding = 'utf-8'
                lines = res.iter_lines()
                iline = 0
                quotes = []
                for line in lines:
                    line = ptf["ptf_id"] + "," + str(line).replace("b'", "").replace("'", "")
                    if "null" in line:
                        continue
                    if iline > 0 and line.find("null") == -1:
                        quote = line.split(",")
                        quotes.append(quote)
                    iline += 1
                # enregistrement dans la table HISTO
                cursor = conn.cursor()
                cursor.executemany("""INSERT INTO HISTO
                    (id, date, open, high, low, close, adjclose, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", quotes)
                conn.commit()
                if len(quotes) == 0:
                    print(" Erreur quotes {}".format(ptf["ptf_id"]))
                    exit(1)
            except BaseException as e:
                print(traceback.format_exc())
                conn.rollback()
                conn.close()
                exit(1)
            else:
                conn.commit()
            finally:
                conn.close()

    def quotes(self):
        conn = self.crud.open_pg()
        try:
            ptfs = self.crud.sql_to_dict("pg", """
            SELECT * FROM ptf where ptf_enabled = '1'
            --AND ptf_id = 'FLTR.L'
            ORDER BY ptf_id
            """, {})
            # Partage du header et du cookie entre toutes les requêtes
            header, crumb, cookies = self.cpu.get_crumbs_and_cookies('ACA.PA')

            # Suppression des records de HISTONEW
            cursor = conn.cursor()
            cursor.execute("DELETE FROM QUOTESNEW", [])
            conn.commit()

            self.pout("Load QuotesNew of")
            qlast = self.crud.get_config("qlast_quotes")
            for ptf in ptfs:
                self.pout(" {}".format(ptf["ptf_id"]))
                # Chargement de l'historique
                # remplissage de la table quotes - dernière quote dans self.quote
                self.quotes_load(ptf, 14, header, cookies)
            self.display("")
            # suppression de la dernière cotation pour intégrer la cotation du jour
            cursor.execute("""
            delete from quotes where date in (select max(date) from quotes)
            """, {})
            conn.commit()
            # insertion des nouvelles cotations sans la table QUOTES
            cursor.execute("""
            insert into QUOTES select * from QUOTESNEW ON CONFLICT DO NOTHING
            """, {})
            conn.commit()
            # calcul rsi et candle(s)
            self.pout("Compute Quotes of")
            for ptf in ptfs:
                self.pout(" {}".format(ptf["ptf_id"]))
                close, close1, rsi, trend, candle0, candle1, candle2 = self.quotes_compute(ptf)

                # maj quote et gain du jour dans ptf
                cursor = conn.cursor()
                cursor.execute("""
                update ptf set ptf_quote = %(close)s::numeric, ptf_gain = ((%(close)s::numeric-%(close1)s::numeric)/%(close1)s::numeric)*100, ptf_candle0 = %(candle0)s, ptf_candle1 = %(candle1)s, ptf_candle2 = %(candle2)s, ptf_rsi = %(rsi)s, ptf_trend = %(trend)s
                where ptf_id = %(id)s
                """, {"id": ptf["ptf_id"], "close1": close1, "close": close, "candle0": candle0, "candle1": candle1, "candle2": candle2, "rsi": rsi, "trend": trend})
                conn.commit()
            # maj orders quote et gain en cours
            cursor.execute("""
            update orders set orders_quote =
            (select close from quotes where id = orders_ptf_id and date = (select max(date) from quotes where id = orders_ptf_id))
            where orders_sell_time is null or orders_sell_time = ''
            """, {})
            conn.commit()
            conn.execute("""
            update orders set orders_gain = orders_quote * orders_quantity - orders_buy * orders_quantity - orders_buy * orders_quantity * %(cost)s - orders_quote * orders_quantity * %(cost)s
            """, {"cost": self.crud.get_config("cost")})
            conn.commit()
            cursor.execute("""
            update orders set orders_gainp = (orders_gain / (orders_buy * orders_quantity)) * 100
            """, {})
            conn.commit()
            cursor.execute("""
            update orders set orders_debit = orders_buy * orders_quantity + orders_buy * orders_quantity * %(cost)s
            """, {"cost": self.crud.get_config("cost")})
            conn.commit()
        except BaseException as e:
            print(traceback.format_exc())
            conn.rollback()
            conn.close()
            exit(1)
        else:
            conn.commit()
        finally:
            conn.close()

        self.display("")

    def quotes_load(self, ptf, nbj, header, cookies):
        """
        Récupération des derniers cours d'une action
        """
        # end_date = int(time.mktime(datetime.datetime.now().timetuple()))
        end_date = int(time.time())
        start_date = int(time.mktime((datetime.datetime.now() - datetime.timedelta(days=nbj)).timetuple()))

        url = "https://query1.finance.yahoo.com/v7/finance/download/{}?period1={}&period2={}&interval=1d&events=history"\
        .format(ptf["ptf_id"], start_date, end_date)
        # self.display(url)
        with requests.Session() as req:
            conn = self.crud.open_pg()
            try:
                res = req.get(url, headers=header, cookies=cookies)
                for block in res.iter_content(256):
                    if b'error' in block:
                        raise ValueError("ERREUR yahoo %s" % block)

                if res.encoding is None:
                    res.encoding = 'utf-8'
                lines = res.iter_lines()
                iline = 0
                quotes = []
                for line in lines:
                    line = ptf["ptf_id"] + "," + str(line).replace("b'", "").replace("'", "")
                    if "null" in line:
                        continue
                    if iline > 0 and line.find("null") == -1:
                        quote = line.split(",")
                        if float(quote[2]) > 0.0:
                            # print(quote)
                            quotes.append(quote)
                    iline += 1
                # enregistrement dans QUOTES
                cursor = conn.cursor()
                cursor.executemany("""INSERT INTO QUOTESNEW
                    (id, date, open, high, low, close, adjclose, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", quotes)
                conn.commit()
                if len(quotes) == 0:
                    print(" Erreur quotes {}".format(ptf["ptf_id"]))
                    exit(1)
            except BaseException as e:
                print(traceback.format_exc())
                conn.rollback()
                conn.close()
                exit(1)
            else:
                conn.commit()
            finally:
                conn.close()

    def quotes_yf(self):
        df = yf.download("ACA.PA", period="1mo")
        sql_texts = []
        for index, row in df.iterrows():       
            sql_texts.append('INSERT INTO PICSOU (date, open, high, low, close, adjclose, volume) VALUES (\'' + index.strftime("%Y-%m-%d") + '\', '+ str(tuple(row.values)) + ')')        
        print('\n\n'.join(sql_texts))

    def display(self, msg, with_date=True):
        """ docstring """
        if with_date==True :
            print("{} : {}".format( str(datetime.datetime.now())[:19], msg))
        else:
            print(msg)
    def pout(self, msg):
        """ docstring """
        sys.stdout.write(msg)
        sys.stdout.flush()

    def __init__(self, args):

        self.args = args
        # load cpu
        # self.cpu = Cpu()

        # Chargement des paramètres
        # self.crud = Crud(args=self.args)

        self.display("Picsou en action...")

        if self.args.test:
            print("test ok")

        if self.args.histo:
            self.histo(self.args.histo)

        if self.args.quotes:
            # self.quotes()
            self.quotes_yf()

        self.display("Picsou en relache")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='picsou_batch')
    # add a -c/--color option
    parser.add_argument('-test', action='store_true', default=False, help="Test environnement")
    parser.add_argument('-histo', type=str, help="Récupération de l'historique d'une valeur")
    parser.add_argument('-histograph', action='store_true', default=False, help="Graphique historique")
    parser.add_argument('-quotes', action='store_true', default=False, help="Récupération des cours du jour")
    parser.add_argument('-quotesgraph', action='store_true', default=False, help="Graphiques QUOTES")
    # print parser.parse_args()
    if parser._get_args() == 0:
        parser.print_help()
    else:
        Picsou(parser.parse_args())
