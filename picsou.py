#./venv/bin/python3
# -*- coding:Utf-8 -*-
"""
    Batch de mise à jour des données de la base
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
from crud import Crud

class Picsou():
    """ Actualisation des données """
    # Planification dans cron
    # 55 9,11,16 * * 1-5 /home/pi/git/crudenome/picsou_batch.py -quote -trade -sms
    # 55 17 * * 1-5 /home/pi/git/crudenome/picsou_batch.py -quote -trade -sms -mail

    def __init__(self, args):

        self.args = args
        # Chargement des paramètres
        self.crud = Crud()

        application = self.crud.get_json_content(
            self.crud.config["application_directory"] + "/" + "picsou.json")

        self.crud.set_application(application)

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
        Calcul des chandeliers 
        """
        quotes = self.crud.sql_to_dict(self.crud.get_basename(), """
        SELECT * FROM quotes order by name ,date asc
        """, {})
        ope_0 = 0
        ope_1 = 0
        ope_2 = 0
        ope_3 = 0
        max_0 = 0
        max_1 = 0
        max_2 = 0
        max_3 = 0
        min_0 = 0
        min_1 = 0
        min_2 = 0
        min_3 = 0
        clo_0 = 0
        clo_1 = 0
        clo_2 = 0
        clo_3 = 0
        if len(quotes) > 0:
            name = ""
            for quote in quotes:
                # rotation
                if name == "" or name != quote["name"]:
                    ope_0 = 0
                    ope_1 = 0
                    ope_2 = 0 
                    ope_3 = 0       
                    min_0 = 0
                    min_1 = 0
                    min_2 = 0
                    min_3 = 0       
                    max_0 = 0
                    max_1 = 0
                    max_2 = 0
                    max_3 = 0       
                    clo_0 = 0
                    clo_1 = 0
                    clo_2 = 0
                    clo_3 = 0
                    name = quote["name"]
                ope_3 = ope_2
                ope_2 = ope_1
                ope_1 = ope_0
                max_3 = max_2
                max_2 = max_1
                max_1 = max_0
                min_3 = min_2
                min_2 = min_1
                min_1 = min_0
                clo_3 = clo_2
                clo_2 = clo_1
                clo_1 = clo_0
                # load
                ope_0 = quote["open"]
                max_0 = quote["high"]
                min_0 = quote["low"]
                clo_0 = quote["close"]
                id = quote["id"]
                date = quote["date"]
                # self.pout("{} {} {} {} {} ...".format(name, ope_0, max_0, min_0, clo_0))
                if ope_3 == 0:
                    continue
                # Traitement des chandeliers
                candle = ""
                # étoîle du soir
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 and ope_1 > clo_2 and ope_1 > ope_0 \
                    and (ope_1-clo_1)/(max_1-min_1) > 0.05:
                    candle = "etoile_du_soir"
                    self.display("{} {} {}".format(name, date, candle))
                # étoîle du matin
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 and clo_1 > ope_2 and ope_1 < clo_0 \
                    and (ope_1-clo_1)/(max_1-min_1) > 0.05:
                    candle = "etoile_du_matin"
                    self.display("{} {} {}".format(name, date, candle))
                # bébé abandonné haussier
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 and ope_1 > clo_2 and ope_1 > ope_0 \
                    and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                    candle = "bebe_abandonne_baissier"
                    self.display("{} {} {}".format(name, date, candle))
                # bébé abandonné baissier
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 and clo_1 > ope_2 and ope_1 < clo_0 \
                    and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                    candle = "bebe_abandonne_haussier"
                    self.display("{} {} {}".format(name, date, candle))
                # avalement haussier
                if clo_1 < ope_1 and clo_0 > ope_0 and ope_0 < clo_1 and clo_0 > ope_1:
                    candle = "avalement_haussier"
                    self.display("{} {} {}".format(name, date, candle))
                # avalement baissier
                if clo_1 > ope_1 and clo_0 < ope_0 and clo_0 < ope_1 and ope_0 > clo_1:
                    candle = "avalement_baissier"
                    self.display("{} {} {}".format(name, date, candle))
                # harami haussier
                if clo_1 < ope_1 and clo_0 > ope_0 and clo_0 < ope_1 and ope_0 > clo_1:
                    candle = "harami_haussier"
                    self.display("{} {} {}".format(name, date, candle))
                # harami baissier
                if clo_1 > ope_1 and clo_0 < ope_0 and ope_0 > clo_1 and clo_0 < ope_1:
                    candle = "harami_baissier"
                    self.display("{} {} {}".format(name, date, candle))
                # les 3 soldats bleus
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 > ope_1 \
                    and ope_1 < clo_2 and ope_1 > ope_2 and clo_1 > clo_2 \
                    and ope_0 < clo_1 and ope_0 > ope_1 and clo_0 > clo_1:
                    candle = "les_3_soldats_bleus"
                    self.display("{} {} {}".format(name, date, candle))
                # les 3 corbeaux rouges
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 < ope_1 \
                    and ope_1 < ope_2 and ope_1 > clo_2 and clo_1 < clo_2 \
                    and ope_0 < ope_1 and ope_0 > clo_1 and clo_0 < clo_1:
                    candle = "les_3_corbeaux_rouges"
                    self.display("{} {} {}".format(name, date, candle))
                # ligne de poussée haussière
                if clo_1 > ope_1 and clo_0 < ope_0 and ope_0 > clo_1 \
                    and clo_0 < clo_1 and clo_0 > ope_1 + (clo_1 - ope_1)/2:
                    candle = "ligne_de_poussee_baissiere"
                    self.display("{} {} {}".format(name, date, candle))
                # ligne de poussée baissière
                if clo_1 < ope_1 and clo_0 > ope_0 and ope_0 < clo_1 \
                    and clo_0 < ope_1 - (ope_1 - clo_1)/2:
                    candle = "ligne_de_poussee_haussiere"
                    self.display("{} {} {}".format(name, date, candle))
                # pénétrante haussière
                if clo_1 < ope_1 and clo_0 > ope_0 \
                    and (clo_0 - ope_0) > (ope_1 - clo_1) \
                    and clo_0 > clo_1 + (ope_1 - clo_1)/2 :
                    candle = "penetrante_haussiere"
                    self.display("{} {} {}".format(name, date, candle))
                # pénétrante baissière
                if clo_1 > ope_1 and clo_0 < ope_0 \
                    and (ope_0 - clo_0) > (clo_1 - ope_1) \
                    and clo_0 < ope_1 + (clo_1 - ope_1)/2 :
                    candle = "penetrante_baissiere"
                    self.display("{} {} {}".format(name, date, candle))

                # maj systématique de candle
                self.crud.exec_sql(self.crud.get_basename(), """
                    update quotes set candle = :candle where id = :id and date = :date
                    """, {"id": id, "date": date, "candle": candle})


    def graphQuotes(self):
        """ """

        def mini_date(sdate):
            return sdate[8:10] + "-" + sdate[5:7]

        self.pout("Graph of")

        seuil_vente = self.crud.get_application_prop("constants")["seuil_vente"]
        seuil_achat = self.crud.get_application_prop("constants")["seuil_achat"]

        # Chargement des commentaires et du top
        ptfs = self.crud.sql_to_dict(self.crud.get_basename(), """
        SELECT ptf.*, orders.orders_order, orders.orders_cost_price, orders.orders_time,
        orders.orders_sell_time 
        FROM ptf LEFT OUTER JOIN orders ON orders_ptf_id = ptf_id and ptf_enabled = 1 ORDER BY ptf_id
        """, {})
        tops = {}
        rems = {}
        orders = {}
        optimum = {}
        cost = {}
        achat = {}
        vente = {}
        seuil = {}
        for ptf in ptfs:
            tops[ptf["ptf_id"]] = ptf["ptf_top"]
            rems[ptf["ptf_id"]] = ptf["ptf_rem"]
            if ptf["orders_order"] is not None:
                orders[ptf["ptf_id"]] = ptf["orders_order"]
            else:
                orders[ptf["ptf_id"]] = ""
            if ptf["orders_time"] is not None:
                achat[ptf["ptf_id"]] = ptf["orders_time"][:10]
            else:
                achat[ptf["ptf_id"]] = "2100:12:31"
            if ptf["orders_sell_time"] is not None:
                vente[ptf["ptf_id"]] = ptf["orders_sell_time"][:10]
            else:
                vente[ptf["ptf_id"]] = "2000:12:31"
            if ptf["orders_cost_price"] is not None:
                optimum[ptf["ptf_id"]] = ptf["orders_cost_price"] + ptf["orders_cost_price"] * seuil_vente
                cost[ptf["ptf_id"]] = ptf["orders_cost_price"]
            else:
                optimum[ptf["ptf_id"]] = 0
                cost[ptf["ptf_id"]] = 0
            if ptf["ptf_seuil_achat"] is not None:
                seuil[ptf["ptf_id"]] = ptf["ptf_seuil_achat"]
            else:
                seuil[ptf["ptf_id"]] = 0
                
        quotes = self.crud.sql_to_dict(self.crud.get_basename(), """
        SELECT quotes.*, ptf_name FROM quotes left outer join ptf on ptf_id = id order by id ,date
        """, {})

        id_current = ""
        dquotes = []
        dachat = []
        dcost = []
        doptimum = []
        dseuil = []
        ddate = []
        dzero = []
        dpercent= []
        dhig_p= []
        dhig_n= []
        dlow_p= []
        dlow_n= []
        dvol = []
        labelx = []
        ptf_name = ""
        qclose1 = 0
        if len(quotes) > 0:
            iquote = 0
            for quote in quotes:
                if id_current == "" : # la 1ère fois
                   id_current = quote["id"]
                   qclose1 = quote["open"]
                   ptf_name = quote["ptf_name"]
                #    self.pout("graphQuotes... " + quote["id"])
                # un graphe par ptf
                if id_current == quote["id"] :
                    # chargement des données
                    # le matin
                    iquote += 1
                    dvol.append(quote["volume"])
                    dquotes.append(quote["open"])
                    if orders[id_current] == "buy" and quote["date"] >= achat[id_current] : 
                        dachat.append(quote["open"])
                    elif orders[id_current] == "sell" and quote["date"] >= achat[id_current] and quote["date"] <= vente[id_current]: 
                        dachat.append(quote["open"])
                    else:
                        dachat.append(None)
                    dcost.append(cost[id_current])
                    doptimum.append(optimum[id_current])
                    dseuil.append(seuil[id_current])
                    ddate.append(mini_date(quote["date"]) + " open")
                    labelx.append(mini_date(quote["date"]))
                    dzero.append(0)
                    percent = ((quote["open"]-qclose1) / qclose1)*100
                    dpercent.append( percent )

                    high = quote["high"] if quote["high"] > quote["open"] else quote["open"]
                    dhig = ((high-qclose1) / qclose1)*100
                    if dhig > 0 :
                        dhig_p.append( dhig )
                        dhig_n.append( 0 )
                    else :
                        dhig_p.append( 0 )
                        dhig_n.append( dhig )
                    low = quote["low"] if quote["low"] < quote["open"] else quote["open"]
                    dlow = ((low-qclose1) / qclose1)*100
                    if dlow > 0 :
                        dlow_p.append( dlow )
                        dlow_n.append( 0 )
                    else :
                        dlow_p.append( 0 )
                        dlow_n.append( dlow )

                    # Le soir
                    iquote += 1
                    dvol.append(quote["volume"])
                    dquotes.append(quote["close"])
                    if orders[id_current] == "buy" and quote["date"] >= achat[id_current] : 
                        dachat.append(quote["close"])
                    elif orders[id_current] == "sell" and quote["date"] >= achat[id_current] and quote["date"] <= vente[id_current]: 
                        dachat.append(quote["close"])
                    else:
                        dachat.append(None)

                    dcost.append(cost[id_current])
                    doptimum.append(optimum[id_current])
                    dseuil.append(seuil[id_current])
                    ddate.append(mini_date(quote["date"]) + " close")
                    labelx.append("")
                    dzero.append(0)
                    percent = ((quote["close"]-qclose1) / qclose1)*100
                    dpercent.append( percent )

                    high = quote["high"] if quote["high"] > quote["open"] else quote["open"]
                    dhig = ((high-qclose1) / qclose1)*100
                    if dhig > 0 :
                        dhig_p.append( dhig )
                        dhig_n.append( 0 )
                    else :
                        dhig_p.append( 0 )
                        dhig_n.append( dhig )

                    low = quote["low"] if quote["low"] < quote["open"] else quote["open"]
                    dlow = ((low-qclose1) / qclose1)*100
                    if dlow > 0 :
                        dlow_p.append( dlow )
                        dlow_n.append( 0 )
                    else :
                        dlow_p.append( 0 )
                        dlow_n.append( dlow )

                    qclose1 = quote["close"]
                    # self.pout(" {}:{}".format(id_current, quote["date"]))
                else:
                    # Dessin du graphe
                    def draw():
                        """ matplotlib. colors
                        b : blue.
                        g : green.
                        r : red.
                        c : cyan.
                        m : magenta.
                        y : yellow.
                        k : black.
                        w : white. """
                        fig, ax1 = plt.subplots()
                        fig.set_figwidth(12)
                        fig.set_figheight(6)

                        ax1.plot(ddate, dquotes, 'mo-', label='Cotation')
                        ax1.plot(ddate, dachat, 'go-', label='Achat', linewidth=2)
                        if orders[id_current] == "buy" :
                            ax1.plot(ddate, dcost, 'g:', label='Seuil rentabilité', linewidth=2)
                            ax1.plot(ddate, doptimum, 'g-', label="Seuil vente {} %".format(seuil_vente*100), linewidth=2)
                        else:
                            if seuil[id_current] != 0:
                                ax1.plot(ddate, dseuil, 'b-', label="Seuil achat {} %".format(seuil_achat*100), linewidth=2)
                        ax1.set_ylabel('Cotation en €', fontsize=9)
                        ax1.tick_params(axis="x", labelsize=8)
                        ax1.tick_params(axis="y", labelsize=8)
                        ax1.legend(loc="lower left")

                        ax2 = ax1.twinx()
                        # ax2.plot(ddate, dzero, 'k:', linewidth=2)
                        ax2.plot(ddate, dpercent, 'bo:', alpha=0.6, label="Pourcentage")
                        ax2.bar(ddate, dhig_p, color='b', alpha=0.2, label="Max.")
                        ax2.bar(ddate, dhig_n, color='r', alpha=0.2, label="Min.")
                        ax2.bar(ddate, dlow_p, color='b', alpha=0.2)
                        ax2.bar(ddate, dlow_n, color='r', alpha=0.2)
                        ax2.set_ylabel('Cotation en %', fontsize=9)
                        ax2.tick_params(axis="y", labelsize=8)
                        # ax2.yaxis.set_ticklabels(dpercent , minor=True)
                        # plt.gca().yaxis.set_ticks(dpercent, minor = True) 
                        ax2.legend(loc="lower right")
                        ax2.grid()

                        ax3 = ax1.twinx()
                        ax3.bar(ddate, dvol, color='k', alpha=0.1, width=0.4, label="Volume")
                        ax3.get_yaxis().set_visible(False)
                        ax3.legend(loc="lower center")

                        fig.autofmt_xdate()
                        plt.subplots_adjust(left=0.06, bottom=0.1, right=0.93, top=0.90, wspace=None, hspace=None)

                        # fig.canvas.draw_idle()
                        plt.xticks(ddate, labelx)
                        # plt.show()
                        # Création du PNG
                        self.pout(" " + id_current + "")
                        # Recherche du fichier qui peut être classé dans un sous répertoire
                        pattern_path = r"\/png\/(.*?){}\.png".format(id_current)
                        comment = ""
                        files = glob.glob(self.crud.get_application_prop("data_directory") + "/png/quotes/**/{}.png".format(id_current), recursive=True)
                        if len(files) == 0:
                            path = "{}/png/quotes/{}.png".format(self.crud.get_application_prop("data_directory"), id_current)
                        else:
                            path = files[0]
                            srep1 = re.search(pattern_path, path).group(1)
                            comment = srep1.replace("quotes", "").replace("/", "")

                        if tops[id_current] == 1 : comment += " TOP"
                        if orders[id_current] == "buy" : comment += " ACHAT"
                        plt.suptitle("Cours de {} - {} - {:3.2f} €".format(id_current, ptf_name, float(dquotes.pop())), fontsize=11, fontweight='bold')
                        title = comment if rems[id_current] is None else comment + " " + rems[id_current]
                        plt.title(title, loc='right', color="black", backgroundcolor="yellow") 
                        plt.savefig(path)
                        plt.close()
                        # Maj de note, seuil_vente dans ptf
                        self.crud.exec_sql(self.crud.get_basename(), """
                        update ptf set ptf_note = :note where ptf_id = :id
                        """, {"id": id_current, "note": comment, "seuil_vente": optimum[id_current]})

                    draw()

                    # ça repart pour un tour
                    # self.pout(" " + quote["id"])
                    dquotes.clear()
                    dachat.clear()
                    doptimum.clear()
                    dseuil.clear()
                    dcost.clear()
                    ddate.clear()
                    dpercent.clear()
                    dhig_p.clear()
                    dhig_n.clear()
                    dlow_p.clear()
                    dlow_n.clear()
                    dzero.clear()
                    dvol.clear()
                    labelx.clear()
                    id_current = quote["id"]
                    qclose1 = quote["open"]
                    ptf_name = quote["ptf_name"]
                    iquote = 0
            if len(dquotes) > 0 : 
                draw()
            self.pout("\n")

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
    # print parser.parse_args()
    if parser._get_args() == 0:
        parser.print_help()
    else:
        Picsou(parser.parse_args())
