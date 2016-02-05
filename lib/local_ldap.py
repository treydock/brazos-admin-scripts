import os
import sys
import ConfigParser
import ldap,pprint
from ldap.controls import SimplePagedResultsControl

class LocalLdap(object):
    def __init__(self, url, use_tls, bind_dn, bind_pass, log_level):
        #ldap.set_option(ldap.OPT_DEBUG_LEVEL,255)
        ldap.set_option(ldap.OPT_REFERRALS, 0)
        try:
            self.l = ldap.initialize(url,trace_level=0)
            self.l.protocol_version = ldap.VERSION3
            if use_tls:
                self.l.start_tls_s()
            if bind_dn and bind_pass:
                self.l.simple_bind_s(bind_dn, bind_pass)
        except ldap.LDAPError as e:
            print e
            sys.exit(1)    


    def paged_search(self, base, sfilter, attrlist, scope='subtree', page_size=1000):
        if scope == 'one':
            _scope = ldap.SCOPE_ONELEVEL
        else:
            _scope = ldap.SCOPE_SUBTREE

        lc = SimplePagedResultsControl(
          ldap.LDAP_CONTROL_PAGE_OID,True,(page_size,'')
        )

        # Send search request
        msgid = self.l.search_ext(
          base,
          _scope,
          sfilter,
          attrlist=attrlist,
          serverctrls=[lc]
        )

        results = []
        pages = 0
        while True:
            pages += 1
            #print "Getting page %d" % (pages,)
            rtype, rdata, rmsgid, serverctrls = self.l.result3(msgid)
            #print '%d results' % len(rdata)
            for dn,data in rdata:
                _r = data
                _r['dn'] = dn
                results.append(_r)
            #results += [i[0] for i in rdata]
            #pprint.pprint(rdata[0])
            pctrls = [
              c
              for c in serverctrls
              if c.controlType == ldap.LDAP_CONTROL_PAGE_OID
            ]
            if pctrls:
                est, cookie = pctrls[0].controlValue
                if cookie:
                    lc.controlValue = (page_size, cookie)
                    msgid = l.search_ext(
                      base,
                      _scope,
                      sfilter,
                      attrlist=attrlist,
                      serverctrls=[lc]
                    )
                else:
                    break
            else:
                print "Warning:  Server ignores RFC 2696 control."
                break
        return results


    def modify(self, dn, attrs):
        self.l.modify_s(dn, attrs)


class LdapObject(object):
    def __init__(self):
        pass

    def setattrs(self, data, listvals=[]):
        #pprint.pprint(data)
        for key,value in data.iteritems():
            if listvals and key in listvals:
                setattr(self, key, value)
            elif type(value) is list:
                setattr(self, key, value[0])
            else:
                setattr(self, key, value)

class LdapUser(LdapObject):
    def __init__(self):
        pass

class LdapGroup(LdapObject):
    def __init__(self):
        pass
