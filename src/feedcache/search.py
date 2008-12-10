# search.py
#
# ...
#
# martind 2008-12-08, 21:28:13
#

from psycopg2.extensions import adapt as psycoadapt
import storm.locals

from feedcache.models.feeds import Entry


__all__ = [
	'Searcher'
]


class Searcher(Exception):
	
	def _pg_wrap_multiword_term(term):
		if term.find(' ') >= 0:
			return u"'%s'" % term
		return term
	
	def _pg_escape_term(term):
		if term==None:
			return None
		return psycoadapt(Searcher._pg_wrap_multiword_term(term)).getquoted()
	
	def _pg_escape_terms(terms):
		return map(Searcher._pg_escape_term, terms)
	
	def _pg_build_query(terms):
		return u"tsv_document @@ (to_tsquery(%s))" % (u') || to_tsquery('.join(Searcher._pg_escape_terms(terms)))
	
	def Entries(store, terms, conditions=True):
		"""
		Returns a Storm ResultSet of Entries, sorted by Entry.date_published (descending).
		"""
		return store.find(
			Entry,
			storm.expr.And(
				conditions,
				Searcher._pg_build_query(terms)
			)
		).order_by(
			storm.expr.Desc(Entry.date_published)
		)
	
	_pg_wrap_multiword_term = staticmethod(_pg_wrap_multiword_term)
	_pg_escape_term = staticmethod(_pg_escape_term)
	_pg_escape_terms = staticmethod(_pg_escape_terms)
	_pg_build_query = staticmethod(_pg_build_query)

	Entries = staticmethod(Entries)
	