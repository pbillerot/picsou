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
# pip install requets
import requests
# pip install matplotlib
import matplotlib.pyplot as plt
# csv
from contextlib import closing
import csv
from codecs import iterdecode

from crud import Crud
from cpu import Cpu

class Picsou():
    """ Actualisation des cours """

    def alphavantage(self):
        """
        Chargement des 100 derniers cours alphavantage
        ATTENTION - il faut passer à PREMIUM pour l'utiliser fréquement
        """
        conn = self.crud.open_pg()
        try:
            ptfs = self.crud.sql_to_dict("pg", """
            SELECT * FROM ptf where ptf_enabled = '1'
            --AND ptf_id = 'SW.PA'
            ORDER BY ptf_id
            """, {})

            # Suppression des records de ALPHAVANTAGE
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ALPHAVANTAGE", [])
            conn.commit()

            self.pout("Alphavantage of")
            for ptf in ptfs:
                self.pout(" {}".format(ptf["ptf_id"]))
                # remplissage de la table histonew
                self.alphavantage_load(ptf)

            # insertion des nouvelles cotations dans la table QUOTES
            # cursor.execute("""
            # insert into QUOTES select * from ALPHAVANTAGE ON CONFLICT DO NOTHING
            # """, {})
            # conn.commit()
            self.display("")

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

    def alphavantage_load(self, ptf):
        """
        Récupération de l'historique via l'api alphavantage
        https://www.alphavantage.co/documentation/
        https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo'
        CSV 0     1    2    3   4     5              6
        timestamp,open,high,low,close,adjusted_close,volume,dividend_amount,split_coefficient
        2023-07-11,96.56,97.56,95.92,97.22,97.22,113607,0.0000,1.0
        """
        url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&outputsize=compact&datatype=csv&symbol={}&apikey={}".format(ptf["ptf_id"], self.crud.get_config("apikey"))
        with requests.get(url, stream=True) as r:
            quotes = []
            conn = self.crud.open_pg()
            try:
                lines = (line.decode('utf-8') for line in r.iter_lines())
                start = True
                for row in csv.reader(lines):
                    if len(row) == 0:
                        continue
                    print(row)
                    if start: # saut de l'entête
                        start = False
                        continue
                    record = [ptf["ptf_id"], row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
                    quotes.append(record)
                cursor = conn.cursor()
                cursor.executemany("""INSERT INTO ALPHAVANTAGE
                    (id, date, open, high, low, close, adjclose, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", quotes)
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
                cursor.executemany("""INSERT INTO HISTONEW
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

    def histo_graph(self):
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
        --and ptf_id = 'CRH.L'
        ORDER BY ptf_id
        """, {})
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
            select * from
            (select * from quotes where id = %(id)s order by date desc limit 340) as quota
            order by id, date
            """, {"id": ptf["ptf_id"]})

            dquotes = []
            ddate = []
            labelx = []
            dmme100 = []
            iquote = 0
            for quote in quotes:
                # chargement des données
                dquotes.append(float(quote["close"]))
                ddate.append(quote["date"])

                # calcul mme100
                if iquote >= 100:
                    dmme100.append(self.cpu.ema(dquotes, 100))
                else:
                    dmme100.append(None)
                # continue
                iquote = iquote + 1

            if len(dquotes) > 0 :
                # DESSIN DU GRAPHE
                """ matplotlib. colors
                b: blue g: green r: red c: cyan m: magenta y: yellow k: black w: white
                """
                fig, ax = plt.subplots()
                fig.set_figwidth(12)
                fig.set_figheight(7)

                plt.suptitle("Historique de {} ({}) du {}".format(ptf["ptf_name"], quote["id"], datetime.datetime.now().strftime("%Y-%m-%d %H:%M")), fontsize=11, fontweight='bold')
                if ptf["ptf_trend"] >= 0:
                    plt.title("Tendance : {:.1f}%".format(ptf["ptf_trend"]), loc='right', pad='10', color="black", fontsize=10, backgroundcolor="paleturquoise")
                else:
                    plt.title("Tendance : {:.1f}%".format(ptf["ptf_trend"]), loc='right', pad='10', color="black", fontsize=10, backgroundcolor="lightpink")

                ax.set_ylabel('Cotation en €', fontsize=9)
                ax.plot(ddate[100:], dmme100[100:], 'g:', label='MME100', linewidth=2)
                ax.plot(ddate[100:], dquotes[100:], 'r-', label='Valeur en €', linewidth=3.0)
                ax.tick_params(axis="x", labelsize=8)
                ax.tick_params(axis="y", labelsize=8)
                ax.yaxis.grid()
                ax.legend(loc="lower left")

                fig.autofmt_xdate()
                plt.subplots_adjust(left=0.06, bottom=0.1, right=0.93, top=0.90, wspace=None, hspace=None)

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
                plt.xticks(ddate[100:], labelx[100:])
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
            ddate.clear()
            labelx.clear()
            dmme100.clear()
        self.pout("\n")

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

    def quotes_compute(self, ptf):
        """
        Calcul RSI et CANDLE(S)
        """
        close0 = 0
        close1 = 0
        candle0 = 0
        candle1 = 0
        candle2 = 0
        rsi = 0
        trend = 0
        conn = self.crud.open_pg()
        try:
            quotes = self.crud.sql_to_dict("pg", """
            select * from
            (select * from quotes where id = %(id)s order by date desc limit 120) as quota
            order by id, date
            """, {"id": ptf["ptf_id"]})
            dfloat = []
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
            iquote = 0
            dfloat = []
            for quote in quotes:
                close1 = close0
                close0 = float(quote["close"])
                dfloat.append(close0)
                if iquote >= 14:
                    rsi = self.cpu.compute_rsi(dfloat, 14)
                if iquote >= 114:
                    trend0 = self.cpu.ema(dfloat, 100)
                    trend1 = self.cpu.ema(dfloat[:iquote-14], 100)
                    trend = (trend0-trend1)*100/trend1

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
                ope_0 = float(quote["open"])
                max_0 = float(quote["high"])
                min_0 = float(quote["low"])
                clo_0 = float(quote["close"])
                # candle
                if quote["id"] == 'STMPA.PA' and quote["date"] == '2023-07-14':
                    pass
                # étoîle du soir + + -
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 \
                    and ope_1 > clo_2 and ope_1 > ope_0 :
                    candle = "etoile_du_soir"
                # étoîle du matin - - +
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 \
                    and ope_1 < clo_2 and ope_1 < ope_0 :
                    candle = "etoile_du_matin"
                # # bébé abandonné haussier
                # if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 < ope_0 and ope_1 > clo_2 \
                #     and ope_1 > ope_0 \
                #     and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                #     candle = "bebe_abandonne_baissier"
                # # bébé abandonné baissier
                # if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 > ope_0 and clo_1 > ope_2 and ope_1 < clo_0 \
                #     and (ope_1-clo_1)/(max_1-min_1) < 0.05:
                #     candle = "bebe_abandonne_haussier"
                # avalement haussier  rouge bleu
                if ope_1 > clo_1 and clo_0 > ope_0 \
                    and ope_0 < clo_1 and clo_0 > ope_1 \
                    and ope_2 > clo_2 \
                        :
                    candle = "avalement_haussier"
                # avalement baissier bleu rouge
                if clo_1 > ope_1 and ope_0 > clo_0 \
                    and clo_0 < ope_1 and ope_0 > clo_1 \
                    and clo_2 > ope_2 \
                        :
                    candle = "avalement_baissier"
                # harami haussier bleu rouge
                if ope_1 < clo_1 and clo_0 > ope_0 and clo_0 < ope_1 and ope_0 > clo_1 \
                    and ope_2 > clo_2 :
                    candle = "harami_haussier"
                # harami baissier rouge bleu
                if clo_1 > ope_1 and clo_0 > ope_0 and ope_0 > ope_1 and clo_0 < clo_1 \
                    and clo_2 > ope_2 :
                    candle = "harami_baissier"
                # les 3 soldats bleus
                if clo_2 > ope_2 and clo_1 > ope_1 and clo_0 > ope_0 \
                    and ope_1 < clo_2 and ope_1 > ope_2 and clo_1 > clo_2 \
                    and ope_0 < clo_1 and ope_0 > ope_1 and clo_0 > clo_1 \
                        :
                    candle = "les_3_soldats_bleus"
                # les 3 corbeaux rouges
                if clo_2 < ope_2 and clo_1 < ope_1 and clo_0 < ope_0 \
                    and ope_1 < ope_2 and ope_1 > clo_2 and clo_1 < clo_2 \
                    and ope_0 < ope_1 and ope_0 > clo_1 and clo_0 < clo_1 \
                        :
                    candle = "les_3_corbeaux_rouges"
                # poussée baissiere rouge > bleu
                if ope_1 > clo_1 and clo_0 > ope_0 \
                    and clo_0 > clo_1 \
                    and clo_0 < ope_1 - (ope_1 - clo_1)/2 \
                    and ope_0 < clo_1 \
                    and (ope_1 - clo_1) > (clo_0 - ope_0 ) \
                        :
                    candle = "poussee_baissiere"
                # poussée haussiere bleu > rouge
                if clo_1 > ope_1 and ope_0 > clo_0 \
                    and ope_0 > clo_1 \
                    and clo_0 < clo_1 \
                    and clo_0 > ope_1 + (clo_1 - ope_1)/2 \
                    and (clo_1 - ope_1) > (ope_0 - clo_0 ) \
                        :
                    candle = "poussee_haussiere"
                # pénétrante baissière bleu < rouge
                if clo_1 > ope_1 and ope_0 > clo_0 \
                    and ope_0 > clo_1 \
                    and clo_0 < clo_1 \
                    and clo_0 > ope_1 + (clo_1 - ope_1)/2 \
                    :
                    candle = "penetrante_baissiere"
                # pénétrante haussière rouge > bleu
                # https://www.centralcharts.com/fr/gm/1-apprendre/7-analyse-technique/28-chandeliers-japonais/548-chandeliers-japonais-penetrante-haussiere
                if ope_1 < clo_1 and clo_0 > ope_0 \
                    and clo_0 < ope_1 and clo_0 > clo_1 + (ope_1 - clo_1)/2 \
                    and ope_0 < ope_1 \
                    and (clo_1 - ope_1) > (ope_0 - clo_0 ) \
                        :
                    candle = "penetrante_haussiere"
                # rotation des candles
                candle2 = candle1
                candle1 = candle0
                candle0 = candle
                # continue
                iquote = iquote+1
        except BaseException as e:
            print(traceback.format_exc())
            conn.rollback()
            conn.close()
            exit(1)
        else:
            conn.commit()
        finally:
            conn.close()
        return close0, close1, rsi, trend, candle0, candle1, candle2

    def quotes_graph(self):
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

        ptfs = self.crud.sql_to_dict("pg", """
        SELECT ptf.*, orders.orders_order, orders.orders_cost_price, orders.orders_time
        FROM ptf LEFT OUTER JOIN orders ON orders_ptf_id = ptf_id
        and orders_order = 'buy' and (orders_sell_time is null or orders_sell_time = '')
        WHERE ptf_enabled = 1
        --and ptf_id = 'CRH.L'
        ORDER BY ptf_id
        """, {})
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
            select * from
            (select * from quotes where id = %(id)s order by date desc limit 80) as quota
            order by id, date
            """, {"id": ptf["ptf_id"]})

            dquotes = []
            doptimum = []
            dseuil = []
            ddate = []
            drsi = []
            dlabelx = []
            candles = []
            dcolors = []
            dmacd = []
            dsignal = []
            dscatter = []
            iquote = 0
            for quote in quotes:
                # chargement des données
                dquotes.append(quote["open"])
                candles.append([quote["low"],quote["adjclose"],quote["open"],quote["high"]])
                if quote["open"] >= quote["close"]:
                    dcolors.append("r")
                else:
                    dcolors.append("b")

                if border and quote["date"] >= order_date:
                        doptimum.append(optimum[quote["id"]])
                        dseuil.append(seuil[quote["id"]])
                else:
                    doptimum.append(None)
                    dseuil.append(None)

                ddate.append(mini_date(quote["date"]))
                dlabelx.append(mini_date(quote["date"]))
                dscatter.append(None)

                # calcul RSI MACD SIGNAL
                if iquote >= 14:
                    drsi.append(self.cpu.compute_rsi(dquotes, 14))
                else:
                    drsi.append(0)
                if iquote >= 26:
                    dmacd.append(self.cpu.ema(dquotes, 12)-self.cpu.ema(dquotes, 26))
                else:
                    dmacd.append(0)
                if iquote >= (26+9):
                    dsignal.append(self.cpu.ema(dmacd, 9))
                else:
                    dsignal.append(0)
                # continue
                iquote = iquote + 1

            if len(dquotes) > 0 :
                # DESSIN DU GRAPHE
                # avant de commancer calcul de l'objectif fictif sur la dernière cotation
                """ matplotlib. colors
                b: blue g: green r: red c: cyan m: magenta y: yellow k: black w: white
                """
                fig, ax = plt.subplots()
                fig.set_figwidth(12)
                fig.set_figheight(7)

                plt.suptitle("Cours de {} - {} - {:.2f} € du {}".format(quote["id"], ptf["ptf_name"], quote["close"], datetime.datetime.now().strftime("%Y-%m-%d %H:%M")), fontsize=11, fontweight='bold')
                plt.title(ptf["ptf_rem"], loc='right', pad='10', color="black", fontsize=10, backgroundcolor="yellow")

                ax.set_ylabel('Cotation en €', fontsize=9)
                ax.tick_params(axis="x", labelsize=8)
                ax.tick_params(axis="y", labelsize=8)
                # SEUIL si achat
                if border:
                    ione = len(dseuil[35:]) - dseuil[35:].count(None)
                    if ione > 1:
                        ax.plot(ddate[35:], doptimum[35:], 'g-', label="Seuil vente {:.1f} %".format(seuil_vente*100), linewidth=2)
                        ax.plot(ddate[35:], dseuil[35:], 'g:', label='Seuil rentabilité', linewidth=2)
                    else:
                        ax.scatter(ddate[35:], doptimum[35:], c="g", marker="^", label="Seuil vente {:.1f} %".format(seuil_vente*100))
                        ax.scatter(ddate[35:], dseuil[35:], c="g", marker="v", label='Seuil rentabilité')
                else:
                    # SCATTER sur la dernière date
                    # https://www.python-simple.com/python-matplotlib/scatterplot.php
                    dscatter[len(dquotes)-1] = dquotes[len(dquotes)-1]+dquotes[len(dquotes)-1]*seuil_vente
                    ax.scatter(ddate[35:], dscatter[35:], c="g", marker="^", label="Point à +{:.1f} %".format(seuil_vente*100))
                ax.legend(loc="lower left")

                # CANDLES
                positions = list(range(0, len(ddate[35:])))
                ax4 = ax.boxplot(candles[35:], positions=positions, patch_artist=True, whis=1, showfliers=False)
                for patch, color in zip(ax4['boxes'], dcolors[35:]):
                     patch.set_facecolor(color)

                # RSI
                ax2 = ax.twinx()
                ax2.plot(ddate[35:], drsi[35:], 'c-', label='RSI')
                ax2.set_ylim(0, 100)
                ax2.set_ylabel('RSI', fontsize=9)
                ax2.tick_params(axis="y", labelsize=8)
                ax2.legend(loc="lower right")
                ax2.grid()

                # MACD
                ax3 = ax.twinx()
                dgreen = []
                dred = []
                for i in range(len(dmacd)):
                    if dmacd[i]-dsignal[i] >= 0:
                        dgreen.append(dmacd[i]-dsignal[i])
                        dred.append(0)
                    else:
                        dgreen.append(0)
                        dred.append(dmacd[i]-dsignal[i])
                # ax3.plot(ddate[35:], dmacd[35:], 'y-', label='MACD')
                ax3.bar(ddate[35:], dgreen[35:], color='#26a69a', alpha=0.2, label="MACD >0")
                ax3.bar(ddate[35:], dred[35:], color='#ef5350', alpha=0.2, label="MACD <0")
                ax3.get_yaxis().set_visible(False)
                ax3.legend(loc="lower center")

                fig.autofmt_xdate()
                plt.subplots_adjust(left=0.06, bottom=0.1, right=0.93, top=0.90, wspace=None, hspace=None)

                plt.xticks(ddate[35:], dlabelx[35:])

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
            drsi.clear()
            dlabelx.clear()
            candles.clear()
            dcolors.clear()
            dmacd.clear()
            dsignal.clear()
            dscatter.clear()
        self.pout("\n")

    def graph_analyse_echo(self):
        """
            Récupération des graphiques sur investir.lesechos.fr
            sur 1 an
            https://investir.lesechos.fr/charts/gif/FR0000120578.gif
            https://investir.lesechos.fr/cours/actions/sanofi-san-fr0000120578-xpar
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
                print(traceback.format_exc())
                conn.close()
                exit(1)
            else:
                if response.status_code == 200:
                    path = "{}/png/ana/{}.gif".format(self.crud.get_config("data_directory"), ptf["ptf_id"])
                    response.raw.decode_content = True
                    with open(path,'wb') as f:
                        shutil.copyfileobj(response.raw, f)
                else:
                    self.pout(" err:{}".format(response.status_code))

        self.pout("\n")

    def graph_from_boursier(self):
        """
        Récupération historique et analyse technique sur boursier.com
        https://www.boursier.com/actions/privileges/analyse-technique/<air-liquide>-<FR0000120073>,FR.html
        https://regex101.com/
        https://cdn-static.boursier.com/illustrations/feeds/daybyday/at/13554120230207050050.gif
        regexp ".*/daybyday\/.*\/(.+?).gif.*"gm
        """
        header, crumb, cookies = self.cpu.get_crumbs_and_cookies_of_url("https://www.boursier.com/")
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
        self.cpu = Cpu()

        # Chargement des paramètres
        self.crud = Crud(args=self.args)

        self.display("Picsou en action...")

        if self.args.test:
            print("test ok")

        if self.args.quotes:
            self.quotes()

        if self.args.quotesgraph:
            self.quotes_graph()

        if self.args.alphavantage:
            self.alphavantage()

        if self.args.histo:
            self.histo()

        if self.args.histograph:
           self.histo_graph()

        self.display("Picsou en relache")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='picsou_batch')
    # add a -c/--color option
    parser.add_argument('-test', action='store_true', default=False, help="Test environnement")
    parser.add_argument('-alphavantage', action='store_true', default=False, help="Récupération de l'historique des cours chez Alphavantage ")
    parser.add_argument('-histo', action='store_true', default=False, help="Récupération de l'historique des cours")
    parser.add_argument('-histograph', action='store_true', default=False, help="Graphique historique")
    parser.add_argument('-quotes', action='store_true', default=False, help="Récupération des cours du jour")
    parser.add_argument('-quotesgraph', action='store_true', default=False, help="Graphiques QUOTES")
    # print parser.parse_args()
    if parser._get_args() == 0:
        parser.print_help()
    else:
        Picsou(parser.parse_args())
