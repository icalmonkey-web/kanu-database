import unittest
from reconcile_evidenced_links import reconcile

class EvidencedLinkTests(unittest.TestCase):
    def test_generic_wallet_name_does_not_attach_unrelated_card(self):
        data = {'cards':[{'id':'pi','bank':'玉山銀行','cardName':'E.SUN Pi Wallet credit card'}],
                'rules':[{'id':'r','title':'玉山Wallet優惠','unresolvedCardId':'ESUN_WALLET','cardId':None}]}
        self.assertEqual(reconcile(data),[])
        self.assertIsNone(data['rules'][0]['cardId'])

    def test_distinctive_product_requires_legacy_and_title(self):
        data = {'cards':[{'id':'c','bank':'國泰世華','cardName':'國泰世華 CUBE 信用卡'}],
                'rules':[{'id':'r','title':'CUBE卡指定消費','unresolvedCardId':'cathay_cube','cardId':None,
                          'sourceUrl':'https://bank.test/terms','quickSearchEligible':True}]}
        self.assertEqual(len(reconcile(data)),1)
        self.assertEqual(data['rules'][0]['cardId'],'c')
