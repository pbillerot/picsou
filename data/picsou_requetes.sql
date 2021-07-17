update cdays set cdays_date = '2020-03-29', cdays_time = '2020-03-29 ' || substr(cdays_time,12)

select * from PTF
--where ptf_id = 'ACA.PA'
order by ptf_id

select cours_ptf_id, cours_name, cours_date, cours_close, cours_rsi, cours_ema12, cours_ema26, cours_ema50, cours_trade, cours_nbj, cours_gain from cours 
where cours_ptf_id = 'AC.PA'
--and cours_trade in ('SSS','RRR','TTT')
--where cours_trade in ('RRR')
--where cours_rsi < 35 --and cours_trade = ''
order by cours_date, cours_ptf_id
--select min(cours_gain) from cours

select * from quotes 
where id = 'VIE.PA'
order by id, date ASC

WITH recursive TT(name, id) AS
(
	select distinct cours_name, cours_ptf_id from cours
	where cours_name is not null
	group by cours_name, cours_ptf_id
)
UPDATE COURS
SET cours_name = (select name from TT where id = cours_ptf_id)
WHERE cours_name is null

WITH recursive TT(id) AS
(
	select cours_id, cours_ptf_id, cours_date  from cours
	order by cours_date desc, cours_ptf_id 
)
-- On ne garde que les 14 derniers cours
delete from COURS where cours_id not in
(
	select A.cours_id  
	from COURS as A
	left join COURS as B
	on A.cours_ptf_id = B.cours_ptf_id and A.cours_date <= B.cours_date
	group by A.cours_id
	having count(*) <= 14
	order by A.cours_ptf_id, A.cours_date desc
)

select * from ptf where ptf_quantity > 0
select sum(ptf_gain) from ptf where ptf_quantity > 0

select * from ptf
--update ptf set ptf_date = ''
where ptf_id in ( select code || '.PA' from cac40)
select * from cac40
where code || '.PA' not in ( select ptf_id from ptf)

CREATE UNIQUE INDEX PTF_INDEX ON ptf (ptf_id)
update ptf set ptf_rsi = 0, ptf_q12 = 0, ptf_q26 = 0

select max(nb) from (
select cours_date, count(*) as nb
from cours
where cours_trade <> ''
group by cours_dates
) as t

select count(*) as nb, sum(cours_gain) as gain from cours where cours_trade = 'RRR'

SELECT cours.cours_id, cours.cours_ptf_id, cours.cours_name, cours.cours_date, cours.cours_close, cours.cours_rsi 
FROM cours
WHERE (cours.cours_name like '%bol%')
ORDER BY cours.cours_ptf_id, cours.cours_date desc LIMIT 400