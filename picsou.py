#./venv/bin/python3
# -*- coding:Utf-8 -*-
"""
    Batch de mise à jour des données de la base picsou
"""
import shutil
import os
import matplotlib as mpl
if os.environ.get('DISPLAY','') == '':
    # print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import datetime, time
import argparse
import sys
import glob
import re
import requests
import random
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
# import pandas as pd
# import pandas_ta as ta
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

        # application = self.crud.get_json_content(
        #     self.crud.config["application_directory"] + "/" + "picsou.json")

        # self.crud.set_application(application)

        self.display("Picsou en action...")

        if self.args.quotes:
            self.quotes()

        if self.args.graph:
           self.graphQuotes()

        if self.args.analyse:
           self.graphFromBoursier()

        if self.args.note:
           self.update_note()

        if self.args.chandeliers:
           self.chandeliers()

        if self.args.quotescandle:
            self.quotes()
            self.chandeliers()

        if self.args.quotesgraph:
            self.quotes()
            self.chandeliers()
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
                self.crud.logger.error("Error %s %s", ValueError, url)
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
            conn = None
            try:
                res = req.get(url, headers=header, cookies=cookies)
                for block in res.iter_content(256):
                    if b'error' in block:
                        raise ValueError("ERREUR yahoo %s" % block)
                # with open("quote.txt", 'wb') as handle:
                #     for block in res.iter_content(1024):
                #         handle.write(block)

                if res.encoding is None:
                    res.encoding = 'utf-8'
                lines = res.iter_lines()
                iline = 0
                quotes = []
                for line in lines:
                    line = ptf["ptf_id"] + "," + ptf["ptf_name"] + "," + str(line).replace("b'", "").replace("'", "")
                    if "null" in line:
                        continue
                    if iline > 0 and line.find("null") == -1:
                        quotes.append(line.split(","))
                        # print line.split(",")
                    iline += 1
                conn = sqlite3.connect(self.crud.get_basename())
                cursor = conn.cursor()
                cursor.execute("DELETE FROM QUOTES WHERE id = ?", (ptf["ptf_id"],))
                cursor.executemany("""INSERT INTO QUOTES 
                    (id, name, date, open, high, low, close, adjclose, volume) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", quotes)
                conn.commit()
                if len(quotes) == 0:
                    self.crud.logger.error("Erreur quotes %s", ptf["ptf_id"])
                    exit(1)
                else:
                    # on alimente quote avec la dernière cotation
                    # pour récup dans picsou_batch
                    col_csv = ['id', 'name', 'date', 'open', 'high', 'low', 'close', 'adj close', 'volume']
                    self.quote = dict(zip(col_csv, quotes.pop()))
            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                self.crud.logger.error("execSql Error %s", e.args[0])
                sys.exit(1)
            except ValueError:
                self.crud.logger.error("Error %s %s", ValueError, url)
            finally:
                if conn:
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

    def quotes(self):       
        ptfs = self.crud.sql_to_dict(self.crud.get_basename(), """
        SELECT * FROM ptf where ptf_enabled = '1' ORDER BY ptf_id
        """, {})
        # Partage du header et du cookie entre toutes les requêtes
        header, crumb, cookies = self.get_crumbs_and_cookies('ACA.PA')
        
        self.pout("Quote of")
        for ptf in ptfs:
            self.pout(" {}".format(ptf["ptf_id"]))
            close1_last = 0.0
            # Chargement de l'historique
            qlast = self.crud.get_application_prop("constants")["qlast_quotes"]
            # remplissage de la table quotes - dernière quote dans self.quote
            self.csv_to_quotes(ptf, qlast, header, cookies) 

            # Calcul du percent par rapport à la veille
            cours = self.crud.sql_to_dict(self.crud.get_basename(), """
            SELECT * FROM quotes WHERE id = :id order by id ,date
            """, {"id": ptf["ptf_id"]})
            if len(cours) > 0:
                close1 = 0.0
                for quote in cours:
                    if close1 == 0.0 : 
                        close1 = quote["open"]
                    self.crud.exec_sql(self.crud.get_basename(), """
                    update quotes set close1 = :close1 where id = :id and date = :date
                    """, {"id": quote["id"], "close1": close1, "date": quote["date"]})
                    close1_last = close1
                    close1 = quote["close"]

            # Suppression des cours des jours antérieurs
            # self.crud.exec_sql(self.crud.get_basename(), """
            # delete from cdays
            # where cdays_date <> date('now')
            # """, {})
            # insertion du dernier cours récupéré dans self.quote
            # self.crud.exec_sql(self.crud.get_basename(), """
            # insert into cdays
            # (cdays_ptf_id, cdays_name, cdays_date, cdays_close
            # , cdays_open, cdays_volume, cdays_low, cdays_high, cdays_time, cdays_close1)
            # select id, name, date, close, open, volume, low, high, datetime('now', 'localtime'), close1
            # from quotes
            # where quotes.id = :id and quotes.date = date('now')
            # """, {"id": ptf["ptf_id"]})

            self.crud.exec_sql(self.crud.get_basename(), """
            update ptf set ptf_quote = :close where ptf_id = :id
            """, {"id": ptf["ptf_id"], "close": self.quote["close"]})
            self.crud.exec_sql(self.crud.get_basename(), """
            update ptf set ptf_gain = ((:close-:close1)/:close1)*100 where ptf_id = :id
            """, {"id": ptf["ptf_id"], "close1": close1_last, "close": self.quote["close"]})

            # self.pout(" {}/{}".format(self.quote["close"], close1_last))

        # calcul cours_percent
        # self.crud.exec_sql(self.crud.get_basename(), """
        # UPDATE cdays
        # set cdays_percent = ( (cdays_close - cdays_close1) / cdays_close1) * 100 
        # """, {})

        self.display("")

    def update_note(self):
        """ Mise à jour du champ note avec des infos pertinentes pour le trading """
        ptfs = self.crud.sql_to_dict(self.crud.get_basename(), """
            SELECT * FROM ptf where ptf_enabled = '1' order by ptf_id
            """, {})
        for ptf in ptfs:
            quotes = self.crud.sql_to_dict(self.crud.get_basename(), """
            SELECT * FROM quotes where id = :id order by date desc limit 1
            """, {"id": ptf["ptf_id"]})
            if quotes is None : continue
            quote = quotes[0]
            """
            - P4 : si quotemin < -4 %
            - Q0 : si quotemin < 0 et close > close1
            """
            note = ""
            pmin = (quote["low"] - quote["close1"])/quote["close1"]
            if float(pmin) < -0.04 : note = "P4"
            if quote["low"] < quote["close1"] and quote["close"] > quote["close1"] :
                note += " Q+"
            self.crud.exec_sql(self.crud.get_basename(), """
                update ptf set ptf_note = :note where ptf_id = :id
                """, {"id": ptf["ptf_id"], "note": note})
            if note != "" :
                self.display("{} : {}".format(ptf["ptf_id"], note))

    # Récupération des graphiques sur investir.lesechos.fr
    # sur 1 an
    def graphAnalyseEcho(self):
        """ 
        "url": "https://investir.lesechos.fr/charts/gif/{_ptf_isin}.gif",       
        """

        ptfs = self.crud.sql_to_dict(self.crud.get_basename(), """
        SELECT * FROM ptf where ptf_enabled = '1' ORDER BY ptf_id
        """, {})
        self.pout("Graph of")
        for ptf in ptfs:
            self.pout(" " + ptf["ptf_id"] + "")
            url = "https://investir.lesechos.fr/charts/gif/{}.gif".format(ptf["ptf_isin"])
            try:
                response = requests.get(url, stream = True)
            except Exception as ex:
                self.crud.logger.error("%s %s %s", ptf["ptf_id"], url, getattr(ex, 'message', repr(ex)))
                self.pout(getattr(ex, 'message', repr(ex)))
            else:
                if response.status_code == 200:
                    path = "{}/png/ana/{}.gif".format(self.crud.get_application_prop("data_directory"), ptf["ptf_id"])
                    response.raw.decode_content = True
                    with open(path,'wb') as f:
                        shutil.copyfileobj(response.raw, f)
                else:
                    self.crud.logger.error("%s %s %s", ptf["ptf_id"], response.status_code, url)
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

        ptfs = self.crud.sql_to_dict(self.crud.get_basename(), """
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
                    self.crud.exec_sql(self.crud.get_basename(), """
                    update ptf set ptf_url_analyse = :url where ptf_id = :id
                    """, {"id": ptf["ptf_id"], "url": url_analyse})
            # grah histo
            url_histo = "https://cdn-graph.boursier.com/Chart.aspx?p=nbcnormal&qt=candle&vt=line&pla1=2&pld1=1&s1={},FR&xx={}&d=974,680,0&gd=71&g=qv&rnd={}".format(ptf["ptf_isin"], str(start_date_histo)[:10], random.randrange(10000))

            # Maj ptf_url_analyse ptf_url_histo
            self.crud.exec_sql(self.crud.get_basename(), """
            update ptf set ptf_url_analyse = :url_analyse, ptf_url_histo = :url_histo where ptf_id = :id
            """, {"id": ptf["ptf_id"], "url_analyse": url_analyse, "url_histo": url_histo})

            time.sleep(1) # wait 1 seconds

        self.pout("\n")

    def chandeliers(self):
        """ 
        Calcul des chandeliers et RSI
        """
        self.pout("Candles of")
        quotes = self.crud.sql_to_dict(self.crud.get_basename(), """
        SELECT * FROM quotes join ptf on ptf_id = id and ptf_enabled = 1 
        order by name ,date asc
        """, {})
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
        candle_0 = ""
        candle_1 = ""
        candle_2 = ""
        dquotes = []
        iquote = 0
        rsi = 0
        mme12 = 0
        mme26 = 0
        mme9 = 0
        macd = 0
        dmacd = []
        signal = 0
        if len(quotes) > 0:
            id = ""
            for quote in quotes:
                # rotation
                if id == "" or id != quote["id"]:
                    if id != "":
                        # maj ptf.ptf_candlex
                        self.crud.exec_sql(self.crud.get_basename(), """
                        update ptf set ptf_candle0 = :candle0, ptf_candle1 = :candle1, ptf_candle2 = :candle2, ptf_rsi = :rsi
                        where ptf_id = :id 
                        """, {"id": id, "candle0": candle_0, "candle1": candle_1, "candle2": candle_2, "rsi": rsi})
                    ope_0 = 0
                    ope_1 = 0
                    ope_2 = 0 
                    min_0 = 0
                    min_1 = 0
                    min_2 = 0
                    max_0 = 0
                    max_1 = 0
                    max_2 = 0
                    clo_0 = 0
                    clo_1 = 0
                    clo_2 = 0
                    candle_0 = ""
                    candle_1 = ""
                    candle_2 = ""
                    id = quote["id"]
                    dquotes.clear()
                    iquote = 0
                    rsi = 0
                    mme12 = 0
                    mme26 = 0
                    mme9 = 0
                    macd = 0
                    dmacd.clear()
                    signal = 0
                    self.pout(" {}".format(id))

                # rotation
                ope_2 = ope_1
                ope_1 = ope_0
                max_2 = max_1
                max_1 = max_0
                min_2 = min_1
                min_1 = min_0
                clo_2 = clo_1
                clo_1 = clo_0
                candle_2 = candle_1
                candle_1 = candle_0
                # initialisation
                ope_0 = quote["open"]
                max_0 = quote["high"]
                min_0 = quote["low"]
                clo_0 = quote["close"]
                id = quote["id"]
                date = quote["date"]
                dquotes.append(quote["close"])
                candle_0 = ""
                iquote += 1
                if ope_2 == 0:
                    continue
                # RSI
                if iquote >= 12:
                    rsi = self.compute_rsi(dquotes)
                    mme12 = self.ema(dquotes, 12)
                    #rsi = self.calcStochRSI(pd.DataFrame({"close": dquotes}))
                if iquote >= 26:
                    mme26 = self.ema(dquotes, 26)
                    macd = mme12-mme26
                    dmacd.append(macd)
                if iquote >= (26+9):
                    signal = self.ema(dmacd, 9)
                #self.display("{} {} MME12:{:.2f} MME26:{:.2f} MACD:{:.2f} SIGNAL:{:.2f}".format(id, date, mme12, mme26, macd, signal))                    
                # Traitement des chandeliers
                # étoîle du soir
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 and ope_1 > clo_2 and ope_1 > ope_0 \
                    and (ope_1-clo_1)/(max_1-min_1) > 0.05:
                    candle_0 = "etoile_du_soir"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # étoîle du matin
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 and clo_1 > ope_2 and ope_1 < clo_0 \
                    and (ope_1-clo_1)/(max_1-min_1) > 0.05:
                    candle_0 = "etoile_du_matin"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # bébé abandonné haussier
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 and ope_1 > clo_2 and ope_1 > ope_0 \
                    and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                    candle_0 = "bebe_abandonne_baissier"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # bébé abandonné baissier
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 and clo_1 > ope_2 and ope_1 < clo_0 \
                    and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                    candle_0 = "bebe_abandonne_haussier"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # avalement haussier
                if clo_1 < ope_1 and clo_0 > ope_0 and ope_0 < clo_1 and clo_0 > ope_1:
                    candle_0 = "avalement_haussier"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # avalement baissier
                if clo_1 > ope_1 and clo_0 < ope_0 and clo_0 < ope_1 and ope_0 > clo_1:
                    candle_0 = "avalement_baissier"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # harami haussier
                if clo_1 < ope_1 and clo_0 > ope_0 and clo_0 < ope_1 and ope_0 > clo_1:
                    candle_0 = "harami_haussier"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # harami baissier
                if clo_1 > ope_1 and clo_0 < ope_0 and ope_0 > clo_1 and clo_0 < ope_1:
                    candle_0 = "harami_baissier"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # les 3 soldats bleus
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 > ope_1 \
                    and ope_1 < clo_2 and ope_1 > ope_2 and clo_1 > clo_2 \
                    and ope_0 < clo_1 and ope_0 > ope_1 and clo_0 > clo_1:
                    candle_0 = "les_3_soldats_bleus"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # les 3 corbeaux rouges
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 < ope_1 \
                    and ope_1 < ope_2 and ope_1 > clo_2 and clo_1 < clo_2 \
                    and ope_0 < ope_1 and ope_0 > clo_1 and clo_0 < clo_1:
                    candle_0 = "les_3_corbeaux_rouges"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # poussée haussière
                if clo_1 > ope_1 and clo_0 < ope_0 \
                    and clo_0 > ope_1 + (clo_1 - ope_1)/2 \
                    and ope_0 > clo_1 + (clo_1 - ope_1)/2:
                    candle_0 = "poussee_baissiere"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # poussée baissière
                if clo_1 < ope_1 and clo_0 > ope_0 \
                    and clo_0 > ope_1 + (clo_1 - ope_1)/2 \
                    and ope_0 > clo_1 + (clo_1 - ope_1)/2:
                    candle_0 = "poussee_haussiere"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # pénétrante haussière
                if clo_1 < ope_1 and clo_0 > ope_0 \
                    and (clo_0 - ope_0) > (ope_1 - clo_1) \
                    and clo_0 > clo_1 + (ope_1 - clo_1)/2 :
                    candle_0 = "penetrante_haussiere"
                    # self.display("{} {} {}".format(id, date, candle_0))
                # pénétrante baissière
                if clo_1 > ope_1 and clo_0 < ope_0 \
                    and (ope_0 - clo_0) > (clo_1 - ope_1) \
                    and clo_0 < ope_1 + (clo_1 - ope_1)/2 :
                    candle_0 = "penetrante_baissiere"
                    # self.display("{} {} {}".format(id, date, candle_0))

                # maj systématique de candle
                # self.display("{} {} rsi:{}".format(id, date, rsi))
                self.crud.exec_sql(self.crud.get_basename(), """
                    update quotes set candle = :candle, rsi = :rsi, macd = :macd, signal = :signal where id = :id and date = :date
                    """, {"id": id, "date": date, "candle": candle_0, "rsi": rsi, "macd": macd, "signal": signal})
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

        seuil_vente = self.crud.get_application_prop("constants")["seuil_vente"]
        seuil_achat = self.crud.get_application_prop("constants")["seuil_achat"]

        # Chargement des commentaires et du top
        ptfs = self.crud.sql_to_dict(self.crud.get_basename(), """
        SELECT ptf.*, orders.orders_order, orders.orders_cost_price, orders.orders_time,
        orders.orders_sell_time 
        FROM ptf LEFT OUTER JOIN orders ON orders_ptf_id = ptf_id WHERE ptf_enabled = 1 
        ORDER BY ptf_id
        """, {})
        # and ptf_id = "STMPA.PA"
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
                optimum[ptf["ptf_id"]] = ptf["orders_cost_price"] + ptf["orders_cost_price"] * seuil_vente
                seuil[ptf["ptf_id"]] = ptf["orders_cost_price"]
            else:
                optimum[ptf["ptf_id"]] = 0
                seuil[ptf["ptf_id"]] = 0
                
            quotes = self.crud.sql_to_dict(self.crud.get_basename(), """
            SELECT * FROM quotes where id = :id order by id ,date
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
                candles.append([quote["low"],quote["close"],quote["open"],quote["high"]])
                if quote["open"] >= quote["close"]:
                    colors.append("r")
                else:
                    colors.append("b")

                if border:
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

                # ax.plot(ddate[35:], dquotes[35:], 'mo-', label='Cotation')
                ax.set_ylabel('Cotation en €', fontsize=9)
                ax.plot(ddate[35:], dseuil[35:], 'g:', label='Seuil rentabilité', linewidth=2)
                ax.plot(ddate[35:], doptimum[35:], 'g-', label="Seuil vente {:.1f} %".format(seuil_vente*100), linewidth=2)
                ax.tick_params(axis="x", labelsize=8)
                ax.tick_params(axis="y", labelsize=8)
                ax.legend(loc="lower left")
                
                positions = list(range(0, len(ddate[35:])))
                ax4 = ax.boxplot(candles[35:], positions=positions, patch_artist=True, whis=1)
                for patch, color in zip(ax4['boxes'], colors):
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
                files = glob.glob(self.crud.get_application_prop("data_directory") + "/png/quotes/**/{}.png".format(quote["id"]), recursive=True)
                if len(files) == 0:
                    path = "{}/png/quotes/{}.png".format(self.crud.get_application_prop("data_directory"), quote["id"])
                else:
                    path = files[0]
                    srep1 = re.search(pattern_path, path).group(1)
                    comment = srep1.replace("quotes", "").replace("/", "")

                plt.suptitle("Cours de {} - {} - {:3.2f} €".format(quote["id"], ptf["ptf_name"], float(dquotes.pop())), fontsize=11, fontweight='bold')
                plt.title(ptf["ptf_rem"], loc='right', color="black", backgroundcolor="yellow") 
                plt.savefig(path)
                plt.close()



                # Maj de note, seuil_vente dans ptf
                # self.crud.exec_sql(self.crud.get_basename(), """
                # update ptf set ptf_note = :note where ptf_id = :id
                # """, {"id": quote["id"], "note": comment, "seuil_vente": optimum[quote["id"]]})

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
    parser.add_argument('-sms', action='store_true', default=False, help="Envoi de SMS de recommandation")
    parser.add_argument('-graph', action='store_true', default=False, help="Création graphique derniers cours")
    parser.add_argument('-note', action='store_true', default=False, help="Mise à jour du bloc note")
    parser.add_argument('-quotes', action='store_true', default=False, help="Récupération des cours du jour")
    parser.add_argument('-analyse', action='store_true', default=False, help="Récupération des graphiques d'analyse")
    parser.add_argument('-chandeliers', action='store_true', default=False, help="Analyse des chandeliers")
    parser.add_argument('-quotescandle', action='store_true', default=False, help="Récup quotes puis Analyse des chandeliers")
    parser.add_argument('-quotesgraph', action='store_true', default=False, help="Enchainement quotes chandeliers graph")
    parser.add_argument('-debug', action='store_true', default=False, help="debug = true en mode debug ")
    # print parser.parse_args()
    if parser._get_args() == 0:
        parser.print_help()
    else:
        Picsou(parser.parse_args())
