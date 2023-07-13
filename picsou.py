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
# pip install requets
import requests
# pip install matplotlib
import matplotlib.pyplot as plt
import numpy as np
# csv
from contextlib import closing
import csv
from codecs import iterdecode

from crud import Crud

class Picsou():
    """ Actualisation des données """
    # Planification dans cron
    # 55 9,11,16 * * 1-5 /home/pi/git/crudenome/picsou_batch.py -quote -trade -sms
    # 55 17 * * 1-5 /home/pi/git/crudenome/picsou_batch.py -quote -trade -sms -mail

    def __init__(self, args):

        self.args = args
        # Chargement des paramètres
        self.crud = Crud(args=self.args)

        self.display("Picsou en action...")

        if self.args.test:
            print("test ok")

        if self.args.histo:
            self.histo()

        if self.args.quotes:
            self.quotes()

        if self.args.graph:
           self.graphQuotes()

        if self.args.graphhisto:
           self.graphHisto()

        if self.args.analyse:
           self.graphFromBoursier()

        if self.args.quotesgraph:
            self.quotes()
            self.graphQuotes()

        self.display("Picsou en relache")

    def get_crumbs_and_cookies(self, stock):
      """
      get crumb and cookies for historical data csv download from yahoo finance
      parameters: stock - short-handle identifier of the company
      returns a tuple of header, crumb and cookie
      """
      url = 'https://finance.yahoo.com/quote/{}/history'.format(stock)
      with requests.session():
        header = {'Connection': 'keep-alive',
                   'Expires': '-1',
                   'Upgrade-Insecure-Requests': '1',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) \
                   AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
                   }

        website = requests.get(url, headers=header)
        # soup = BeautifulSoup(website.text, 'lxml')
        # crumb = re.findall('"CrumbStore":{"crumb":"(.+?)"}', str(soup))

        # return (header, crumb[0], website.cookies)
        return (header, '', website.cookies)

    def get_crumbs_and_cookies_of_url(self, url):
      """
      get crumb and cookies for historical data csv download from yahoo finance
      parameters: stock - short-handle identifier of the company
      returns a tuple of header, crumb and cookie
      """
      with requests.session():
        header = {'Connection': 'keep-alive',
                   'Expires': '-1',
                   'Upgrade-Insecure-Requests': '1',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) \
                   AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
                   }

        website = requests.get(url, headers=header)
        return (header, '', website.cookies)

    def get_content_form_url(self, url, header, cookies):
        """
        Obtenir le contenu d'une requête http(s)
        """
        content = ""
        with requests.Session() as req:
            conn = None
            try:
                res = req.get(url, headers=header, cookies=cookies)
                content = res.content.decode("utf-8")
            except ValueError:
                print(" Error {} {}".format(ValueError, url))
        return content

    def get_bytes_form_url(self, url):
        """
        Obtenir le contenu d'une requête http(s)
        """
        with requests.Session() as req:
            header = {'Connection': 'keep-alive',
                'Expires': '-1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
            }
            res = req.get(url, headers=header)
        return res.content

    def csv_to_histo_old(self, ptf, nbj):
        """
        Récupération de l'historique via l'api alphavantage
        https://www.alphavantage.co/documentation/
        https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo'
        CSV 0     1    2    3   4     5              6
        timestamp,open,high,low,close,adjusted_close,volume,dividend_amount,split_coefficient
        2023-07-11,96.56,97.56,95.92,97.22,97.22,113607,0.0000,1.0
        """
        url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&outputsize=full&datatype=csv&symbol={}&apikey={}".format(ptf["ptf_id"], self.crud.get_config("apikey"))
        with requests.get(url, stream=True) as r:
            quotes = []
            conn = self.crud.open_pg()
            try:
                lines = (line.decode('utf-8') for line in r.iter_lines())
                start = True
                for row in csv.reader(lines):
                    if start:
                        start = False
                        continue
                    record = [ptf["ptf_id"], row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
                    quotes.append(record)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM HISTO WHERE id = %s", [ptf["ptf_id"]])
                cursor.executemany("""INSERT INTO HISTO
                    (id, date, open, high, low, close, adjclose, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", quotes)
                conn.commit()
                if len(quotes) == 0:
                    print(" Erreur quotes {}".format(ptf["ptf_id"]))
                    exit(1)
            except BaseException as e:
                print(" Error {}".format(e))
                conn.rollback()
            else:
                conn.commit()
            finally:
                conn.close()

    def csv_to_histo(self, ptf, nbj, header, cookies):
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
                        # print line.split(",")
                    iline += 1
                # enregistrement dans la table HISTO
                cursor = conn.cursor()
                cursor.execute("DELETE FROM HISTO WHERE id = %s", [ptf["ptf_id"]])
                cursor.executemany("""INSERT INTO HISTO
                    (id, date, open, high, low, close, adjclose, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", quotes)
                conn.commit()
                if len(quotes) == 0:
                    print(" Erreur quotes {}".format(ptf["ptf_id"]))
                    exit(1)
            except BaseException as e:
                print("csv_to_histo Error {}".format(e))
                conn.rollback()
            else:
                conn.commit()
            finally:
                conn.close()

    def csv_to_quotes(self, ptf, nbj, header, cookies):
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
                closes = []
                close1 = '0.0'
                for line in lines:
                    line = ptf["ptf_id"] + "," + str(line).replace("b'", "").replace("'", "")
                    if "null" in line:
                        continue
                    if iline > 0 and line.find("null") == -1:
                        quote = line.split(",")
                        quote.append(str(close1))
                        quotes.append(quote)
                        closes.append(float(quote[5]))
                        close1 = quote[5]
                        # print line.split(",")
                    iline += 1
                # calcul candle 012 rsi macd signal
                rsi = 0
                mme12 = 0
                mme26 = 0
                mme9 = 0
                macd = 0
                dmacd = []
                signal = 0
                iquote = 0
                ope_0 = 0
                ope_1 = 0
                ope_2 = 0
                max_0 = 0
                max_1 = 0
                max_2 = 0
                min_0 = 0
                min_1 = 0
                min_2 = 0
                clo_0 = 0
                clo_1 = 0
                clo_2 = 0
                for quote in quotes:
                    if iquote >= 12:
                        mme12 = self.ema(closes[:iquote+1], 12)
                    if iquote >= 14:
                        rsi = self.compute_rsi(closes[:iquote+1])
                    if iquote >= 26:
                        mme26 = self.ema(closes[:iquote+1], 26)
                        macd = mme12-mme26
                        dmacd.append(macd)
                    if iquote >= (26+9):
                        signal = self.ema(dmacd, 9)
                    quotes[iquote].append(str(rsi))
                    quotes[iquote].append(str(macd))
                    quotes[iquote].append(str(signal))
                    # Traitement des chandeliers
                    #           2     3     4    5      6         7       8       9    10    11      12
                    # id, date, open, high, low, close, adjclose, volume, close1, rsi, macd, signal, candle
                    # étoîle du soir
                    candle = ""
                    # rotation
                    ope_2 = ope_1
                    ope_1 = ope_0
                    max_2 = max_1
                    max_1 = max_0
                    min_2 = min_1
                    min_1 = min_0
                    clo_2 = clo_1
                    clo_1 = clo_0
                    # valorisation
                    ope_0 = float(quote[2])
                    max_0 = float(quote[3])
                    min_0 = float(quote[4])
                    clo_0 = float(quote[5])
                    # candle
                    if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 and ope_1 > clo_2 and ope_1 > ope_0 \
                        and (ope_1-clo_1)/(max_1-min_1) > 0.05:
                        candle = "etoile_du_soir"
                    # étoîle du matin
                    if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 and clo_1 > ope_2 and ope_1 < clo_0 \
                        and (ope_1-clo_1)/(max_1-min_1) > 0.05:
                        candle = "etoile_du_matin"
                    # bébé abandonné haussier
                    if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 and ope_1 > clo_2 and ope_1 > ope_0 \
                        and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                        candle = "bebe_abandonne_baissier"
                    # bébé abandonné baissier
                    if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 and clo_1 > ope_2 and ope_1 < clo_0 \
                        and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                        candle = "bebe_abandonne_haussier"
                    # avalement haussier
                    if clo_1 < ope_1 and clo_0 > ope_0 and ope_0 < clo_1 and clo_0 > ope_1:
                        candle = "avalement_haussier"
                    # avalement baissier
                    if clo_1 > ope_1 and clo_0 < ope_0 and clo_0 < ope_1 and ope_0 > clo_1:
                        candle = "avalement_baissier"
                    # harami haussier
                    if clo_1 < ope_1 and clo_0 > ope_0 and clo_0 < ope_1 and ope_0 > clo_1:
                        candle = "harami_haussier"
                    # harami baissier
                    if clo_1 > ope_1 and clo_0 < ope_0 and ope_0 > clo_1 and clo_0 < ope_1:
                        candle = "harami_baissier"
                    # les 3 soldats bleus
                    if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 > ope_0 \
                        and ope_1 < clo_2 and ope_1 > ope_2 and clo_1 > clo_2 \
                        and ope_0 < clo_1 and ope_0 > ope_1 and clo_0 > clo_1:
                        candle = "les_3_soldats_bleus"
                    # les 3 corbeaux rouges
                    if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 < ope_0 \
                        and ope_1 < ope_2 and ope_1 > clo_2 and clo_1 < clo_2 \
                        and ope_0 < ope_1 and ope_0 > clo_1 and clo_0 < clo_1:
                        candle = "les_3_corbeaux_rouges"
                    # poussée haussière
                    if clo_1 > ope_1 and clo_0 < ope_0 \
                        and clo_0 > ope_1 + (clo_1 - ope_1)/2 \
                        and ope_0 > clo_1 + (clo_1 - ope_1)/2:
                        candle = "poussee_baissiere"
                    # poussée baissière
                    if clo_1 < ope_1 and clo_0 > ope_0 \
                        and clo_0 > ope_1 + (clo_1 - ope_1)/2 \
                        and ope_0 > clo_1 + (clo_1 - ope_1)/2:
                        candle = "poussee_haussiere"
                    # pénétrante haussière
                    if clo_1 < ope_1 and clo_0 > ope_0 \
                        and (clo_0 - ope_0) > (ope_1 - clo_1) \
                        and clo_0 > clo_1 + (ope_1 - clo_1)/2 :
                        candle = "penetrante_haussiere"
                    # pénétrante baissière
                    if clo_1 > ope_1 and clo_0 < ope_0 \
                        and (ope_0 - clo_0) > (clo_1 - ope_1) \
                        and clo_0 < ope_1 + (clo_1 - ope_1)/2 :
                        candle = "penetrante_baissiere"
                    quotes[iquote].append(candle)
                    iquote = iquote+1
                # enregistrement dans QUOTES
                cursor = conn.cursor()
                cursor.execute("DELETE FROM QUOTES WHERE id = %s", [ptf["ptf_id"]])
                cursor.executemany("""INSERT INTO QUOTES
                    (id, date, open, high, low, close, adjclose, volume, close1, rsi, macd, signal, candle)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", quotes)
                conn.commit()
                if len(quotes) == 0:
                    print(" Erreur quotes {}".format(ptf["ptf_id"]))
                    exit(1)
                else:
                    # on alimente quote avec la dernière cotation
                    # pour récup dans picsou_batch
                    col_csv = ['id', 'date', 'open', 'high', 'low', 'close', 'adjclose', 'volume', 'close1']
                    self.quote = dict(zip(col_csv, quotes.pop()))
            except BaseException as e:
                print("csv_to_quotes Error {}".format(e))
                conn.rollback()
            else:
                conn.commit()
            finally:
                conn.close()

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

    def histo(self):
        ptfs = self.crud.sql_to_dict("sqlite", """
        SELECT * FROM ptf where ptf_enabled = '1'
        ORDER BY ptf_id
        """, {})
        # AND ptf_id = 'SW.PA'
        # Partage du header et du cookie entre toutes les requêtes
        header, crumb, cookies = self.get_crumbs_and_cookies('ACA.PA')

        self.pout("Histo of")
        for ptf in ptfs:
            self.pout(" {}".format(ptf["ptf_id"]))
            # Chargement de l'historique
            nbj = self.crud.get_config("qlast_histo")
            # remplissage de la table histo
            self.csv_to_histo(ptf, nbj, header, cookies)

        self.display("")

    def quotes(self):
        conn = self.crud.open_pg()
        try:
            ptfs = self.crud.sql_to_dict("pg", """
            SELECT * FROM ptf where ptf_enabled = '1'
            ORDER BY ptf_id
            """, {})
            # AND ptf_id = 'SW.PA'
            # Partage du header et du cookie entre toutes les requêtes
            header, crumb, cookies = self.get_crumbs_and_cookies('ACA.PA')

            self.pout("Quote of")
            for ptf in ptfs:
                self.pout(" {}".format(ptf["ptf_id"]))
                close1_last = 0.0
                close1 = 0.0
                # Chargement de l'historique
                qlast = self.crud.get_config("qlast_quotes")
                # remplissage de la table quotes - dernière quote dans self.quote
                self.csv_to_quotes(ptf, qlast, header, cookies)

                # maj quote et gain du jour dans ptf
                cursor = conn.cursor()
                cursor.execute("""
                update ptf set ptf_quote = %(close)s::numeric, ptf_gain = ((%(close)s::numeric-%(close1)s::numeric)/%(close1)s::numeric)*100
                where ptf_id = %(id)s
                """, {"id": ptf["ptf_id"], "close1": self.quote["close1"], "close": self.quote["adjclose"]})
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
            print("quotes Error {}".format(e))
            conn.rollback()
        else:
            conn.commit()
        finally:
            conn.close()

        self.display("")

    # Récupération des graphiques sur investir.lesechos.fr
    # sur 1 an
    def graphAnalyseEcho(self):
        """
        "url": "https://investir.lesechos.fr/charts/gif/{_ptf_isin}.gif",
        """

        ptfs = self.crud.sql_to_dict("sqlite", """
        SELECT * FROM ptf where ptf_enabled = '1' ORDER BY ptf_id
        """, {})
        self.pout("Graph of")
        for ptf in ptfs:
            self.pout(" " + ptf["ptf_id"] + "")
            url = "https://investir.lesechos.fr/charts/gif/{}.gif".format(ptf["ptf_isin"])
            try:
                response = requests.get(url, stream = True)
            except Exception as ex:
                self.pout(getattr(ex, 'message', repr(ex)))
            else:
                if response.status_code == 200:
                    path = "{}/png/ana/{}.gif".format(self.crud.get_config("data_directory"), ptf["ptf_id"])
                    response.raw.decode_content = True
                    with open(path,'wb') as f:
                        shutil.copyfileobj(response.raw, f)
                else:
                    self.pout(" err:{}".format(response.status_code))

        self.pout("\n")

    # Récupération historique et analyse technique sur boursier.com
    def graphFromBoursier(self):
        """
        Récupération historique et analyse technique sur boursier.com
        https://www.boursier.com/actions/privileges/analyse-technique/<air-liquide>-<FR0000120073>,FR.html
        https://regex101.com/
        https://cdn-static.boursier.com/illustrations/feeds/daybyday/at/13554120230207050050.gif
        regexp ".*/daybyday\/.*\/(.+?).gif.*"gm
        """
        header, crumb, cookies = self.get_crumbs_and_cookies_of_url("https://www.boursier.com/")
        start_date_histo = datetime.datetime.now() - datetime.timedelta(weeks=52)

        ptfs = self.crud.sql_to_dict("sqlite", """
        SELECT * FROM ptf where ptf_enabled = '1' ORDER BY ptf_id
        """, {})
        self.pout("Graph of")
        for ptf in ptfs:
            self.pout(" " + ptf["ptf_id"] + "")
            url_analyse = ""
            url_histo = ""
            # graph technique
            url = "https://www.boursier.com/actions/privileges/analyse-technique/{}-{},FR.html".format(ptf["ptf_name"].lower(), ptf["ptf_isin"])
            content = self.get_content_form_url(url, header, cookies)
            if content != "":
                # recup du nom du gif
                gif_names = re.search('.*/daybyday\/.*\/(.+?).gif.*', content)
                # parfois il n'y a pas d'analyse du jour
                if gif_names:
                    gif_name = gif_names.group(1)
                    id_pa = re.search('(.+?)\..*', ptf["ptf_id"]).group(1) # on ne garde que le préfixe au "."
                    url_analyse = "https://cdn-static.boursier.com/illustrations/feeds/daybyday/at/{}.gif".format(gif_name)
                    # Maj ptf_url_analyse
                    self.crud.exec_sql("sqlite", """
                    update ptf set ptf_url_analyse = :url where ptf_id = :id
                    """, {"id": ptf["ptf_id"], "url": url_analyse})
            # grah histo
            url_histo = "https://cdn-graph.boursier.com/Chart.aspx?p=nbcnormal&qt=candle&vt=line&pla1=2&pld1=1&s1={},FR&xx={}&d=974,680,0&gd=71&g=qv&rnd={}".format(ptf["ptf_isin"], str(start_date_histo)[:10], random.randrange(10000))

            # Maj ptf_url_analyse ptf_url_histo
            self.crud.exec_sql("sqlite", """
            update ptf set ptf_url_analyse = :url_analyse, ptf_url_histo = :url_histo where ptf_id = :id
            """, {"id": ptf["ptf_id"], "url_analyse": url_analyse, "url_histo": url_histo})

            time.sleep(1) # wait 1 seconds

        self.pout("\n")

    def graphQuotes(self):
        """
        Création du graphique des cotations avec candle, valeur, volume et rsi
        https://matplotlib.org/stable/gallery/statistics/boxplot_color.html#sphx-glr-gallery-statistics-boxplot-color-py
        https://matplotlib.org/stable/plot_types/stats/boxplot_plot.html#sphx-glr-plot-types-stats-boxplot-plot-py
        https://www.python-simple.com/python-matplotlib/boxplot.php
        """

        def mini_date(sdate):
            return sdate[8:10] + "-" + sdate[5:7]

        self.pout("Graph of")

        seuil_vente = self.crud.get_config("seuil_vente")
        seuil_achat = self.crud.get_config("seuil_achat")

        # Chargement des commentaires et du top
        ptfs = self.crud.sql_to_dict("pg", """
        SELECT ptf.*, orders.orders_order, orders.orders_cost_price, orders.orders_time
        FROM ptf LEFT OUTER JOIN orders ON orders_ptf_id = ptf_id
        and orders_order = 'buy' and (orders_sell_time is null or orders_sell_time = '')
        WHERE ptf_enabled = 1
        ORDER BY ptf_id
        """, {})
        # and ptf_id = "SW.PA"
        optimum = {}
        seuil = {}
        border = False
        btop = False
        order_date = ""
        for ptf in ptfs:
            self.pout(" " + ptf["ptf_id"] + "")

            if ptf["ptf_top"] == "1":
                btop = True
            else:
                btop = False
            if ptf["orders_order"] is not None and ptf["orders_order"] == "buy":
                border = True
            else:
                border = False
            if ptf["orders_cost_price"] is not None:
                optimum[ptf["ptf_id"]] = ptf["orders_cost_price"] + ptf["orders_cost_price"] *  decimal.Decimal(seuil_vente)
                seuil[ptf["ptf_id"]] = ptf["orders_cost_price"]
                order_date = ptf["orders_time"][:10]
            else:
                optimum[ptf["ptf_id"]] = 0
                seuil[ptf["ptf_id"]] = 0

            quotes = self.crud.sql_to_dict("pg", """
            SELECT * FROM quotes where id = %(id)s order by id ,date
            """, {"id": ptf["ptf_id"]})

            dquotes = []
            doptimum = []
            dseuil = []
            ddate = []
            dlow = []
            dhigh = []
            dvol = []
            drsi = []
            labelx = []
            candles = []
            colors = []
            macd = []
            signal = []
            for quote in quotes:
                # chargement des données
                dvol.append(quote["volume"])
                dquotes.append(quote["open"])
                candles.append([quote["low"],quote["adjclose"],quote["open"],quote["high"]])
                if quote["open"] >= quote["close"]:
                    colors.append("r")
                else:
                    colors.append("b")

                if border and quote["date"] >= order_date:
                        doptimum.append(optimum[quote["id"]])
                        dseuil.append(seuil[quote["id"]])
                else:
                    doptimum.append(None)
                    dseuil.append(None)

                ddate.append(mini_date(quote["date"]))
                labelx.append(mini_date(quote["date"]))

                high = quote["high"] #if quote["high"] > quote["open"] else quote["open"]
                dhigh.append(high)
                low = quote["low"] #if quote["low"] < quote["open"] else quote["open"]
                dlow.append(high)
                if quote["rsi"] != 0:
                    drsi.append(quote["rsi"])
                else:
                    drsi.append(None)
                signal.append(quote["signal"])
                macd.append(quote["macd"])

            if len(dquotes) > 0 :
                # DESSIN DU GRAPHE
                """ matplotlib. colors
                b: blue g: green r: red c: cyan m: magenta y: yellow k: black w: white
                """
                fig, ax = plt.subplots()
                fig.set_figwidth(12)
                fig.set_figheight(7)

                plt.suptitle("Cours de {} - {} - {:.2f} € Rsi: {:.0f} Macd: {:.1f}".format(quote["id"], ptf["ptf_name"], quote["close"], quote["rsi"], quote["macd"]-quote["signal"]), fontsize=11, fontweight='bold')
                plt.title(ptf["ptf_rem"], loc='right', pad='10', color="black", fontsize=10, backgroundcolor="yellow")

                ax.set_ylabel('Cotation en €', fontsize=9)
                if border:
                    ax.plot(ddate[35:], dseuil[35:], 'g:', label='Seuil rentabilité', linewidth=2)
                    ax.plot(ddate[35:], doptimum[35:], 'g-', label="Seuil vente {:.1f} %".format(seuil_vente*100), linewidth=2)
                    ax.legend(loc="lower left")
                ax.tick_params(axis="x", labelsize=8)
                ax.tick_params(axis="y", labelsize=8)

                positions = list(range(0, len(ddate[35:])))
                ax4 = ax.boxplot(candles[35:], positions=positions, patch_artist=True, whis=1)
                for patch, color in zip(ax4['boxes'], colors[35:]):
                     patch.set_facecolor(color)

                ax2 = ax.twinx()
                ax2.plot(ddate[35:], drsi[35:], 'c-', label='RSI')
                ax2.set_ylim(0, 100)
                ax2.set_ylabel('RSI', fontsize=9)
                ax2.tick_params(axis="y", labelsize=8)
                ax2.legend(loc="lower right")
                ax2.grid()

                ax3 = ax.twinx()
                dgreen = []
                dred = []
                for i in range(len(macd)):
                    if macd[i]-signal[i] >= 0:
                        dgreen.append(macd[i]-signal[i])
                        dred.append(0)
                    else:
                        dgreen.append(0)
                        dred.append(macd[i]-signal[i])
                # ax3.plot(ddate[35:], dmacd[35:], 'y-', label='MACD')
                ax3.bar(ddate[35:], dgreen[35:], color='#26a69a', alpha=0.2, label="MACD >0")
                ax3.bar(ddate[35:], dred[35:], color='#ef5350', alpha=0.2, label="MACD <0")
                # for i in range(len(macd[35:])):
                #     if macd[i]-signal[i]>0:
                #         ax3.bar(ddate[35:], macd[i]-signal[i], color = '#ef5350')
                #     else:
                #         ax3.bar(ddate[35:], macd[i]-signal[i], color = '#26a69a')
                ax3.get_yaxis().set_visible(False)
                # ax3.set_ylabel('MACD', fontsize=9)
                # ax3.tick_params(axis="y", labelsize=8)
                #ax3.grid()
                ax3.legend(loc="lower center")

                # ax3 = ax.twinx()
                # ax3.bar(ddate[35:], dvol[35:], color='k', alpha=0.1, width=0.4, label="Volume")
                # ax3.get_yaxis().set_visible(False)
                # ax3.legend(loc="lower center")

                fig.autofmt_xdate()
                plt.subplots_adjust(left=0.06, bottom=0.1, right=0.93, top=0.90, wspace=None, hspace=None)

                # fig.canvas.draw_idle()
                plt.xticks(ddate[35:], labelx[35:])
                # plt.show()
                # Création du PNG
                # Recherche du fichier qui peut être classé dans un sous répertoire
                pattern_path = r"\/png\/(.*?){}\.png".format(quote["id"])
                comment = ""
                files = glob.glob(self.crud.get_config("data_directory") + "/png/quotes/**/{}.png".format(quote["id"]), recursive=True)
                if len(files) == 0:
                    path = "{}/png/quotes/{}.png".format(self.crud.get_config("data_directory"), quote["id"])
                else:
                    path = files[0]
                    srep1 = re.search(pattern_path, path).group(1)
                    comment = srep1.replace("quotes", "").replace("/", "")

                plt.savefig(path)
                plt.close()

            # ça repart pour un tour
            dquotes.clear()
            doptimum.clear()
            dseuil.clear()
            ddate.clear()
            dhigh.clear()
            dlow.clear()
            dvol.clear()
            drsi.clear()
            labelx.clear()
            candles.clear()
            colors.clear()
            macd.clear()
            signal.clear()
        self.pout("\n")

    def graphHisto(self):
        """
        Création du graphique des cotations historique 1 an
        """

        def mini_date(sdate):
            return sdate[8:10] + "-" + sdate[5:7]

        self.pout("GraphHisto of")

        seuil_vente = self.crud.get_config("seuil_vente")
        seuil_achat = self.crud.get_config("seuil_achat")

        # Chargement des commentaires et du top
        ptfs = self.crud.sql_to_dict("pg", """
        SELECT ptf.*, orders.orders_order, orders.orders_cost_price, orders.orders_time
        FROM ptf LEFT OUTER JOIN orders ON orders_ptf_id = ptf_id
        and orders_order = 'buy' and (orders_sell_time is null or orders_sell_time = '')
        WHERE ptf_enabled = 1
        ORDER BY ptf_id
        """, {})
        # and ptf_id = "SAN.PA"
        optimum = {}
        seuil = {}
        border = False
        btop = False
        order_date = ""
        for ptf in ptfs:
            self.pout(" " + ptf["ptf_id"] + "")

            if ptf["ptf_top"] == "1":
                btop = True
            else:
                btop = False
            if ptf["orders_order"] is not None and ptf["orders_order"] == "buy":
                border = True
            else:
                border = False
            if ptf["orders_cost_price"] is not None:
                optimum[ptf["ptf_id"]] = ptf["orders_cost_price"] + ptf["orders_cost_price"] * decimal.Decimal(seuil_vente)
                seuil[ptf["ptf_id"]] = ptf["orders_cost_price"]
                order_date = ptf["orders_time"][:10]
            else:
                optimum[ptf["ptf_id"]] = 0
                seuil[ptf["ptf_id"]] = 0

            quotes = self.crud.sql_to_dict("pg", """
            SELECT * FROM histo where id = %(id)s order by id ,date
            """, {"id": ptf["ptf_id"]})

            dquotes = []
            doptimum = []
            dseuil = []
            ddate = []
            dlow = []
            dhigh = []
            dvol = []
            labelx = []
            candles = []
            colors = []
            for quote in quotes:
                # chargement des données
                dvol.append(quote["volume"])
                dquotes.append(quote["open"])
                candles.append([quote["low"],quote["adjclose"],quote["open"],quote["high"]])
                if quote["open"] >= quote["close"]:
                    colors.append("r")
                else:
                    colors.append("b")

                if border and quote["date"] >= order_date:
                        doptimum.append(optimum[quote["id"]])
                        dseuil.append(seuil[quote["id"]])
                else:
                    doptimum.append(None)
                    dseuil.append(None)

                ddate.append(quote["date"])

                high = quote["high"] #if quote["high"] > quote["open"] else quote["open"]
                dhigh.append(high)
                low = quote["low"] #if quote["low"] < quote["open"] else quote["open"]
                dlow.append(high)

            if len(dquotes) > 0 :
                # DESSIN DU GRAPHE
                """ matplotlib. colors
                b: blue g: green r: red c: cyan m: magenta y: yellow k: black w: white
                """
                fig, ax = plt.subplots()
                fig.set_figwidth(12)
                fig.set_figheight(7)

                plt.suptitle("Historique de {} - {}".format(quote["id"], ptf["ptf_name"], quote["close"]), fontsize=11, fontweight='bold')
                plt.title(ptf["ptf_rem"], loc='right', pad='10', color="black", fontsize=10, backgroundcolor="yellow")

                ax.set_ylabel('Cotation en €', fontsize=9)
                ax.plot(ddate, dquotes, 'r-', label='Valeur en €', linewidth=3.0)
                ax.tick_params(axis="x", labelsize=8)
                ax.tick_params(axis="y", labelsize=8)
                ax.yaxis.grid()
                # positions = list(range(0, len(ddate[35:])))
                # ax4 = ax.boxplot(candles[35:], positions=positions, patch_artist=True, whis=1)
                # for patch, color in zip(ax4['boxes'], colors[35:]):
                #      patch.set_facecolor(color)

                # ax2 = ax.twinx()
                # ax2.plot(ddate[35:], drsi[35:], 'c-', label='RSI')
                # ax2.set_ylim(0, 100)
                # ax2.set_ylabel('RSI', fontsize=9)
                # ax2.tick_params(axis="y", labelsize=8)
                # ax2.legend(loc="lower right")
                # ax2.grid()

                # ax3 = ax.twinx()
                # dgreen = []
                # dred = []
                # for i in range(len(macd)):
                #     if macd[i]-signal[i] >= 0:
                #         dgreen.append(macd[i]-signal[i])
                #         dred.append(0)
                #     else:
                #         dgreen.append(0)
                #         dred.append(macd[i]-signal[i])
                # ax3.plot(ddate[35:], dmacd[35:], 'y-', label='MACD')
                # ax3.bar(ddate[35:], dgreen[35:], color='#26a69a', alpha=0.2, label="MACD >0")
                # ax3.bar(ddate[35:], dred[35:], color='#ef5350', alpha=0.2, label="MACD <0")
                # for i in range(len(macd[35:])):
                #     if macd[i]-signal[i]>0:
                #         ax3.bar(ddate[35:], macd[i]-signal[i], color = '#ef5350')
                #     else:
                #         ax3.bar(ddate[35:], macd[i]-signal[i], color = '#26a69a')
                # ax3.get_yaxis().set_visible(False)
                # ax3.set_ylabel('MACD', fontsize=9)
                # ax3.tick_params(axis="y", labelsize=8)
                #ax3.grid()
                # ax3.legend(loc="lower center")

                # ax3 = ax.twinx()
                # ax3.bar(ddate[35:], dvol[35:], color='k', alpha=0.1, width=0.4, label="Volume")
                # ax3.get_yaxis().set_visible(False)
                # ax3.legend(loc="lower center")

                fig.autofmt_xdate()
                plt.subplots_adjust(left=0.06, bottom=0.1, right=0.93, top=0.90, wspace=None, hspace=None)

                # fig.canvas.draw_idle()
                locale.setlocale(locale.LC_ALL, "")
                mm = ""
                for index, label in enumerate(ddate):
                    date = datetime.datetime.strptime(label, '%Y-%m-%d')
                    mmx = date.strftime("%B")
                    if mmx != mm:
                        labelx.append(date.strftime("%B"))
                        mm = mmx
                    else:
                        labelx.append(None)
                plt.tick_params(top=False, bottom=False, left=True, right=False, labelleft=True, labelbottom=True)
                plt.xticks(ddate, labelx)
                # Création du PNG
                # Recherche du fichier qui peut être classé dans un sous répertoire
                pattern_path = r"\/png\/(.*?){}\.png".format(quote["id"])
                comment = ""
                files = glob.glob(self.crud.get_config("data_directory") + "/png/histo/**/{}.png".format(quote["id"]), recursive=True)
                if len(files) == 0:
                    path = "{}/png/histo/{}.png".format(self.crud.get_config("data_directory"), quote["id"])
                else:
                    path = files[0]
                    srep1 = re.search(pattern_path, path).group(1)
                    comment = srep1.replace("quotes", "").replace("/", "")

                plt.savefig(path)
                plt.close()

            # ça repart pour un tour
            dquotes.clear()
            doptimum.clear()
            dseuil.clear()
            ddate.clear()
            dhigh.clear()
            dlow.clear()
            dvol.clear()
            labelx.clear()
            candles.clear()
            colors.clear()
        self.pout("\n")

    def compute_rsi(self, data, n=14):
        deltas = np.diff(data)
        seed = deltas[:n+1]
        up = seed[seed>=0].sum()/n
        down = -seed[seed<0].sum()/n
        rs = up/down
        rsi = np.zeros_like(data)
        rsi[:n] = 100. - 100./(1.+rs)

        for i in range(n, len(data)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up*(n-1) + upval)/n
            down = (down*(n-1) + downval)/n
            rs = up/down
            rsi[i] = 100. - 100./(1.+rs)
        return rsi[len(rsi)-1]

    def ema(self, data, window):
        """ Calculates Exponential Moving Average """
        if len(data) < 2 * window:
            window = len(data)//2
            if window < 2 : return None
            # raise ValueError("data is too short")
        c = 2.0 / (window + 1)
        current_ema = self.sma(data[-window*2:-window], window)
        for value in data[-window:]:
            current_ema = (c * value) + ((1 - c) * current_ema)
        return current_ema

    def sma(self, data, window):
        """ Calculates Simple Moving Average """
        if len(data) < window:
            return sum(data) / float(len(data))
        return sum(data[-window:]) / float(window)

    def calcRSI(self, data, P=14):
        # Calculate gains and losses
        # https://raposa.trade/blog/2-ways-to-trade-the-stochastic-rsi-in-python/
        data['diff_close'] = data['close'] - data['close'].shift(1)
        data['gain'] = np.where(data['diff_close']>0,
            data['diff_close'], 0)
        data['loss'] = np.where(data['diff_close']<0,
            np.abs(data['diff_close']), 0)

        # Get initial values
        data[['init_avg_gain', 'init_avg_loss']] = data[
            ['gain', 'loss']].rolling(P).mean()
        # Calculate smoothed avg gains and losses for all t > P
        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))

        for i, _row in enumerate(data.iterrows()):
            row = _row[1]
            if i < P - 1:
                last_row = row.copy()
                continue
            elif i == P-1:
                avg_gain[i] += row['init_avg_gain']
                avg_loss[i] += row['init_avg_loss']
            else:
                avg_gain[i] += ((P - 1) * avg_gain[i-1] + row['gain']) / P
                avg_loss[i] += ((P - 1) * avg_loss[i-1] + row['loss']) / P

            last_row = row.copy()

        data['avg_gain'] = avg_gain
        data['avg_loss'] = avg_loss
        # Calculate RS and RSI
        data['RS'] = data['avg_gain'] / data['avg_loss']
        data['RSI'] = 100 - 100 / (1 + data['RS'])
        return data

    def calcStochOscillator(self, data, N=14):
        data['low_N'] = data['RSI'].rolling(N).min()
        data['high_N'] = data['RSI'].rolling(N).max()
        data['StochRSI'] = 100 * (data['RSI'] - data['low_N']) / (data['high_N'] - data['low_N'])
        return data

    def calcStochRSI(self, data, P=14, N=14):
        data = self.calcRSI(data, P)
        data = self.calcStochOscillator(data, N)
        return data

    def calcReturns(self, df):
        # Helper function to avoid repeating too much code
        df['returns'] = df['Close'] / df['Close'].shift(1)
        df['log_returns'] = np.log(df['returns'])
        df['strat_returns'] = df['position'].shift(1) * df['returns']
        df['strat_log_returns'] = df['position'].shift(1) * df['log_returns']
        df['cum_returns'] = np.exp(df['log_returns'].cumsum()) - 1
        df['strat_cum_returns'] = np.exp(df['strat_log_returns'].cumsum()) / - 1
        df['peak'] = df['cum_returns'].cummax()
        df['strat_peak'] = df['strat_cum_returns'].cummax()
        return df

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='picsou_batch')
    # add a -c/--color option
    parser.add_argument('-test', action='store_true', default=False, help="Test environnement")
    parser.add_argument('-sms', action='store_true', default=False, help="Envoi de SMS de recommandation")
    parser.add_argument('-graph', action='store_true', default=False, help="Création graphique derniers cours")
    parser.add_argument('-graphhisto', action='store_true', default=False, help="Création graphique historique cours")
    parser.add_argument('-quotes', action='store_true', default=False, help="Récupération des cours du jour")
    parser.add_argument('-histo', action='store_true', default=False, help="Récupération de l'historique des cours")
    parser.add_argument('-analyse', action='store_true', default=False, help="Récupération des graphiques d'analyse")
    parser.add_argument('-quotesgraph', action='store_true', default=False, help="Enchainement quotes graph")
    # print parser.parse_args()
    if parser._get_args() == 0:
        parser.print_help()
    else:
        Picsou(parser.parse_args())
