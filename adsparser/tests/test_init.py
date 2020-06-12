import unittest
import adsparser


class TestServices(unittest.TestCase):
    def test_parse(self):
        for (test, expected) in [('one two', '(one OR two)'),
                                 ('one OR two', 'one OR two'),
                                 ('one NOT three', 'one NOT three'),
                                 ('(one)', 'one'),
                                 ('(one two)', '(one OR two)'),
                                 ('((one two))', '(one OR two)'),
                                 ('(((one two)))', '(one OR two)'),
                                 ('(one (two three))', '(one OR (two OR three))'),
                                 ('(one (two OR three))', '(one OR (two OR three))'),
                                 ('(one (two OR three and four))', '(one OR (two OR three AND four))'),
                                 ('((foo AND bar) OR (baz) OR a OR b OR c)', '((foo AND bar) OR baz OR a OR b OR c)'),
                                 ('LISA +\"gravitational wave\" AND \"gravity wave\"',
                                  '(LISA OR +"gravitational wave") AND "gravity wave"'),
                                 (
                                 "\"lattice green's function\",\"kepler's equation\",\"lattice green function\",\"kepler equation\",\"loop quantum gravity\",\"loop quantum cosmology\",\"random walk\",EJTP",
                                 '("lattice green\'s function" OR "kepler\'s equation" OR "lattice green function" OR "kepler equation" OR "loop quantum gravity" OR "loop quantum cosmology" OR "random walk" OR EJTP)'),
                                 (
                                 '\"shell galaxies\" OR \"shell galaxy\" OR ((ripple OR ripples OR shells OR (tidal AND structure) OR (tidal AND structures) OR (tidal AND feature) OR (tidal AND features)) AND (galaxy OR galaxies))',
                                 '"shell galaxies" OR "shell galaxy" OR ((ripple OR ripples OR shells OR (tidal AND structure) OR (tidal AND structures) OR (tidal AND feature) OR (tidal AND features)) AND (galaxy OR galaxies))'),
                                 ('"Large scale structure",Cl,ELG,"angular power spectrum", [OII], SFR',
                                  '("Large scale structure" OR Cl OR ELG OR "angular power spectrum" OR OII OR SFR)'),
                                 (
                                 'Abundance, Models, "Solar Model", "Oscillator Strength", Abundance, Spectroscopy, "Dissociation Energy",',
                                 '(Abundance OR Models OR "Solar Model" OR "Oscillator Strength" OR Abundance OR Spectroscopy OR "Dissociation Energy")'),
                                 (
                                 '(DISTANCE AND SCALE ) OR (TRGB) ("RED SUPERGIANTS") OR ( ECLIPSING AND BINARY ) OR (EXTRASOLAR AND PLANET) OR SUPERWASP OR EXOPLANET OR IC1613 OR M31 OR NGC6822',
                                 '(DISTANCE AND SCALE) OR TRGB OR "RED SUPERGIANTS" OR (ECLIPSING AND BINARY) OR (EXTRASOLAR AND PLANET) OR SUPERWASP OR EXOPLANET OR IC1613 OR M31 OR NGC6822'),
                                 (
                                 '(nanotube or "domain wall" or "nanowire magnetism" or micromagnetism) and not (carbon) and not (superconductivity or superconductor or Majorana)',
                                 '(nanotube OR "domain wall" OR "nanowire magnetism" OR micromagnetism) AND NOT carbon AND NOT (superconductivity OR superconductor OR Majorana)'),
                                 ('"machine learning" "neural networks" ORCID "text extraction"',
                                  '("machine learning" OR "neural networks" OR ORCID OR "text extraction")'),
                                 ]:
            output = adsparser.parse_classic_keywords(test)

            self.assertEquals(output, expected)

            
    def test_multiline(self):
    	for (test, expected) in [
                ("+EUV coronal waves \r\n +Dimmings\r\nDimming +Mass Evacuation\r\n+Eruption prominence",
                 '(+EUV OR coronal OR waves OR +Dimmings OR Dimming OR +Mass OR Evacuation OR +Eruption OR prominence)'),
                ('"solar flare" OR\r\n"solar dynamo" OR\r\n"magnetic reconnection"',
                 '"solar flare" OR "solar dynamo" OR "magnetic reconnection"'),
        ]:
            output = adsparser.parse_classic_keywords(test)
            self.assertEquals(output, expected)

    def test_singlequote(self):
        for (test, expected) in [
                ("'star formation' cluster region young",
                 '("star formation" OR cluster OR region OR young)'),
                ("'intermediate seyfert' 'seyfert 1.8' 'seyfert'",
                 '("intermediate seyfert" OR "seyfert 1.8" OR "seyfert")'),
                # counter example
                ('+"Sunyaev Zel\'dovich" "green\'s function"',
                 '(+"Sunyaev Zel\'dovich" OR "green\'s function")'),
        ]:
            output = adsparser.parse_classic_keywords(test)
            self.assertEquals(output, expected)

    def test_plus(self):
        for (test, expected) in [
                ('+"Angular Momentum"+"evolution"',
                 '(+"Angular Momentum" OR +"evolution")'),
                ('+cosmology+review',
                 '(+cosmology OR +review)'),
                # counter example
                ("+LBV 'luminous blue variable' or G79.29+0.46",
                 '(+LBV OR "luminous blue variable") OR G79.29+0.46'),
        ]:
            output = adsparser.parse_classic_keywords(test)
            self.assertEquals(output, expected)

    def test_minus(self):
        for (test, expected) in [
                ('exoplanet -star',
                 '(exoplanet -star)'),
                ('exoplanet -"stellar evolution"',
                 '(exoplanet -"stellar evolution")'),
                ('stellar-evolution +exoplanet',
                 '(stellar-evolution OR +exoplanet)'),
                ('-this AND that',
                 '* -this AND that'),
                ('-this OR that AND (-foo OR bar)',
                 '* -this OR that AND (* -foo OR bar)'),
                ('-this that',
                 '(* -this OR that)'),
        ]:
            output = adsparser.parse_classic_keywords(test)
            self.assertEquals(output, expected)
