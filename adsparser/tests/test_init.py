import os
import unittest
import adsparser
import requests
from urllib import urlencode


class TestServices(unittest.TestCase):
    def test_parse(self):
        for (test, expected) in [
                     ('one two', '(one OR two)'),
                     ('one OR two', '(one OR two)'),
                     ('one NOT three', '(one NOT three)'),
                     ('(one)', '(one)'),
                     ('(one two)', '(one OR two)'),
                     ('((one two))', '(one OR two)'),
                     ('(((one two)))', '(one OR two)'),
                     ('(one (two three))', '(one OR (two OR three))'),
                     ('(one (two OR three))', '(one OR (two OR three))'),
                     ('(one (two OR three and four))', '(one OR (two OR three AND four))'),
                     ('((foo AND bar) OR (baz) OR a OR b OR c)', '((foo AND bar) OR baz OR a OR b OR c)'),
                     ('LISA +\"gravitational wave\" AND \"gravity wave\"',
                      '(LISA OR +"gravitational wave" AND "gravity wave")'),
                     (
                     "\"lattice green's function\",\"kepler's equation\",\"lattice green function\",\"kepler equation\",\"loop quantum gravity\",\"loop quantum cosmology\",\"random walk\",EJTP",
                     '("lattice green\'s function" OR "kepler\'s equation" OR "lattice green function" OR "kepler equation" OR "loop quantum gravity" OR "loop quantum cosmology" OR "random walk" OR EJTP)'),
                     (
                     '\"shell galaxies\" OR \"shell galaxy\" OR ((ripple OR ripples OR shells OR (tidal AND structure) OR (tidal AND structures) OR (tidal AND feature) OR (tidal AND features)) AND (galaxy OR galaxies))',
                     '("shell galaxies" OR "shell galaxy" OR ((ripple OR ripples OR shells OR (tidal AND structure) OR (tidal AND structures) OR (tidal AND feature) OR (tidal AND features)) AND (galaxy OR galaxies)))'),
                     ('"Large scale structure",Cl,ELG,"angular power spectrum", [OII], SFR',
                      '("Large scale structure" OR Cl OR ELG OR "angular power spectrum" OR OII OR SFR)'),
                     (
                     'Abundance, Models, "Solar Model", "Oscillator Strength", Abundance, Spectroscopy, "Dissociation Energy",',
                     '(Abundance OR Models OR "Solar Model" OR "Oscillator Strength" OR Abundance OR Spectroscopy OR "Dissociation Energy")'),
                     (
                     '(DISTANCE AND SCALE ) OR (TRGB) ("RED SUPERGIANTS") OR ( ECLIPSING AND BINARY ) OR (EXTRASOLAR AND PLANET) OR SUPERWASP OR EXOPLANET OR IC1613 OR M31 OR NGC6822',
                     '((DISTANCE AND SCALE) OR TRGB OR "RED SUPERGIANTS" OR (ECLIPSING AND BINARY) OR (EXTRASOLAR AND PLANET) OR SUPERWASP OR EXOPLANET OR IC1613 OR M31 OR NGC6822)'),
                     (
                     '(nanotube or "domain wall" or "nanowire magnetism" or micromagnetism) and not (carbon) and not (superconductivity or superconductor or Majorana)',
                     '((nanotube OR "domain wall" OR "nanowire magnetism" OR micromagnetism) AND NOT carbon AND NOT (superconductivity OR superconductor OR Majorana))'),
                     ('"machine learning" "neural networks" ORCID "text extraction"',
                      '("machine learning" OR "neural networks" OR ORCID OR "text extraction")'),
                     ('whistler+"whistler precursor"+reformation+nonstationary',
                      '(whistler OR +"whistler precursor" OR +reformation OR +nonstationary)'),
                    ('("whistler precursor" and shock) or +(whistler and shock) or +(("interplanetary shock" or "bow shock") and whistler) or +("lower hybrid" and shock) or +("modified two stream" and shock) or +("drift instability" and shock)',
                     '(("whistler precursor" AND shock) OR +(whistler AND shock) OR +(("interplanetary shock" OR "bow shock") AND whistler) OR +("lower hybrid" AND shock) OR +("modified two stream" AND shock) OR +("drift instability" AND shock))'),
                    ('(star) +(planet and galaxy)',
                     '(star OR +(planet AND galaxy))'),
                    ('star +(planet and galaxy)',
                     '(star OR +(planet AND galaxy))'),
                    ('star +planet +galaxy',
                     '(star OR +planet OR +galaxy)'),
                    ("+EUV coronal waves",
                     '(+EUV OR coronal OR waves)'),
                ]:
            output = adsparser.parse_classic_keywords(test)

            self.assertEquals(output, expected)


    def test_multiline(self):
        for (test, expected) in [
                ("+EUV coronal waves \r\n +Dimmings\r\nDimming +Mass Evacuation\r\n+Eruption prominence",
                 '(+EUV OR coronal OR waves OR +Dimmings OR Dimming OR +Mass OR Evacuation OR +Eruption OR prominence)'),
                ('"solar flare" OR\r\n"solar dynamo" OR\r\n"magnetic reconnection"',
                 '("solar flare" OR "solar dynamo" OR "magnetic reconnection")'),
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
                ('+star',
                 '(+star)'),
                ('+star+',
                 '(+star)'),
                ('+(star)',
                 '(+star)'),
                ('+(star or planet)',
                 '(+(star OR planet))'),
                ('+star or +planet',
                 '(+star OR +planet)'),
                ('+"Angular Momentum"+"evolution"',
                 '(+"Angular Momentum" OR +"evolution")'),
                ('+cosmology+review',
                 '(+cosmology OR +review)'),
                ## counter example
                ("+LBV 'luminous blue variable' or G79.29+0.46",
                 '(+LBV OR "luminous blue variable" OR G79.29+0.46)'),
        ]:
            output = adsparser.parse_classic_keywords(test)
            self.assertEquals(output, expected)

    def test_equal(self):
        for (test, expected) in [
                ('=star',
                 '(=star)'),
                ('=(star)',
                 '(=star)'),
                ('=(star or planet)',
                 '(=(star OR planet))'),
                ('=star or =planet',
                 '(=star OR =planet)'),
                ('="Angular Momentum"="evolution"',
                 '(="Angular Momentum" OR ="evolution")'),
                ("=star=",
                 '(=star)'),
        ]:
            output = adsparser.parse_classic_keywords(test)
            self.assertEquals(output, expected)

    def test_minus(self):
        for (test, expected) in [
                ('-star',
                 '(* AND -star)'),
                ('-star-',
                 '(* AND -star)'),
                ('-(star)',
                 '(* AND -star)'),
                ('-(star or planet)',
                 '(* AND -(star OR planet))'),
                ('-star or -planet',
                 '(* AND -star OR -planet)'),
                ('exoplanet -star',
                 '(exoplanet AND -star)'),
                ('exoplanet -"stellar evolution"',
                 '(exoplanet AND -"stellar evolution")'),
                ('stellar-evolution +exoplanet',
                 '(stellar-evolution OR +exoplanet)'),
                ('-this AND that',
                 '(that AND -this)'),
                ('-this OR that AND (-foo OR bar)',
                 '((that AND (bar AND -foo)) AND -this)'),
                ('-this that',
                 '(that AND -this)'),
        ]:
            output = adsparser.parse_classic_keywords(test)
            self.assertEquals(output, expected)

    def test_order_minus(self):
        for (test, expected) in [
                ('star AND -planet OR hot',
                 '((star OR hot) AND -planet)'),
                ('(-spectroscopy and galaxy) (-star -planet hot)',
                 '((galaxy AND -spectroscopy) OR (hot AND -star AND -planet))'),
                ('star -planet hot',
                 '((star OR hot) AND -planet)'),
                ('-star -planet hot',
                 '(hot AND -star AND -planet)'),
                ('galaxy (-star -planet hot)',
                 '(galaxy OR (hot AND -star AND -planet))'),
                ('(spectroscopy AND galaxy) (-star -planet hot)',
                 '((spectroscopy AND galaxy) OR (hot AND -star AND -planet))'),
                ('"Blanco 1" "spectroscopic orbits" -supernova -"black hole"',
                 '(("Blanco 1" OR "spectroscopic orbits") AND -supernova AND -"black hole")'),
                ('"Blanco 1" ("spectroscopic orbits" -supernova -"black hole")',
                 '("Blanco 1" OR ("spectroscopic orbits" AND -supernova AND -"black hole"))'),
                ('"Blanco 1" (-"spectroscopic orbits" -supernova -"black hole")',
                 '("Blanco 1" OR (* AND -"spectroscopic orbits" AND -supernova AND -"black hole"))'),
                ('-"Blanco 1" (-"spectroscopic orbits" -supernova -"black hole")',
                 '((* AND -"spectroscopic orbits" AND -supernova AND -"black hole") AND -"Blanco 1")'),
                ]:
            output = adsparser.parse_classic_keywords(test)

            self.assertEquals(output, expected)

    def test_real_user_input(self):
        for (test, expected) in [
                ("``AGN''``black hole''",
                 '("AGN" OR "black hole")'),
                ('"transitinal""gap formation " migration exoplanet protoplanetary fargo',
                 '("transitinal" OR "gap formation " OR migration OR exoplanet OR protoplanetary OR fargo)'),
                ('Seyfert-1',
                 '(Seyfert-1)'),
                ('star or Seyfert-1',
                 '(star OR Seyfert-1)'),
                ('X-ray',
                 '(X-ray)'),
                ('spin and X-ray',
                 '(spin AND X-ray)'),
                ('"X-ray"',
                 '("X-ray")'),
                ("'X-ray'",
                 '("X-ray")'),
                ("UV/X-ray",
                 '(UV/X-ray)'),
                ("'UV/X-ray'",
                 '("UV/X-ray")'),
                ('black and hole spin',
                 '(black AND hole OR spin)'),
                ('black hole spin and UV/X-ray variability or broad-band spectral study of "radio loud narrow line Seyfert-1 galaxy"',
                 '(black OR hole OR spin AND UV/X-ray OR variability OR broad-band OR spectral OR study OR of OR "radio loud narrow line Seyfert-1 galaxy")'),
                ('"high-resolution spectroscopy"',
                 '("high-resolution spectroscopy")'),
                ('+stereoscopic hyperstereo "depth perception" 3D "3-D"',
                 '(+stereoscopic OR hyperstereo OR "depth perception" OR 3D OR "3-D")'),
                ('helioseismology =granulation =granules =granule =granular =supergranulation =supergranules =supergranule =supergranular ="near-surface" convection dynamo ="stellar atmosphere" ="solar rotation" ="stellar rotation"',
                 '(helioseismology OR =granulation OR =granules OR =granule OR =granular OR =supergranulation OR =supergranules OR =supergranule OR =supergranular OR ="near-surface" OR convection OR dynamo OR ="stellar atmosphere" OR ="solar rotation" OR ="stellar rotation")'),
                ('+b-type "hot star" "model atmosphere" magellanic',
                 '(+b-type OR "hot star" OR "model atmosphere" OR magellanic)'),
                ('"soft gamma repeater" magnetar -sgrA "millisecond pulsar" binary',
                 '(("soft gamma repeater" OR magnetar OR "millisecond pulsar" OR binary) AND -sgrA)'),
                ('+"cosmic ray"\r\n"interstellar medium"\r\nicecube\r\nams-02\r\nfermi\r\nanisotropy\r\ndiffusion',
                 '(+"cosmic ray" OR "interstellar medium" OR icecube OR ams-02 OR fermi OR anisotropy OR diffusion)'),
                ('physics,soalphysics,astrophysics',
                 '(physics OR soalphysics OR astrophysics)'),
                ('="Hakamada-Akasofu-Fry"',
                 '(="Hakamada-Akasofu-Fry")'),
                ('galaxy+cluster',
                 '(galaxy OR +cluster)'),
                ('ACCRETION\r\n"ACTIVE GALACTIC NUCLEI"\r\nAGN\r\n"BLACK HOLE" \r\n"COMPACT OBJECT" \r\n"GALAXY CENTER"\r\nJET\r\nKERR\r\n"NEUTRON STAR"\r\nQUASAR\r\nQPO\r\nQUASIPERIODIC\r\nRELATIVITY\r\n"SAGITTARIUS A"\r\nSCHWARZSCHILD\r\nSEYFERT\r\n"X-RAY"\r\n',
                 '(ACCRETION OR "ACTIVE GALACTIC NUCLEI" OR AGN OR "BLACK HOLE" OR "COMPACT OBJECT" OR "GALAXY CENTER" OR JET OR KERR OR "NEUTRON STAR" OR QUASAR OR QPO OR QUASIPERIODIC OR RELATIVITY OR "SAGITTARIUS A" OR SCHWARZSCHILD OR SEYFERT OR "X-RAY")'),
                ('n2h+',
                 '(n2h)'),
                ('^lau, marie wingyee',
                 '(^lau OR marie OR wingyee)'), # Not the ideal translation, but we cannot do better at this point
                ('star] galaxy',
                 '(star OR galaxy)'),
                ('"variable" + period',
                 '("variable" OR +period)'),
                ('AGNs="active galactic nuclei"\r\nQSOs\r\n"X-ray Background"\r\nClustering\r\n"Luminosity Function"\r\n',
                 '(AGNs OR ="active galactic nuclei" OR QSOs OR "X-ray Background" OR Clustering OR "Luminosity Function")'),
                ('+ "dwarf eliptical galaxies"',
                 '(+"dwarf eliptical galaxies")'),
                ('"galaxy cluster" \r\nSunyaev-Zel\'dovich\r\nICM',
                 '("galaxy cluster" OR Sunyaev-Zel\'dovich OR ICM)'),
                ('`NGC 253\' or `NGC 4945\'',
                 '("NGC 253" OR "NGC 4945")'),
                ('starspots"red dwarf"',
                 '(starspots OR "red dwarf")'),
                ('+="space weather"',
                 '(="space weather")'),
                ('blazar quasar agn ``active galactic nuclei\'\' "3C 454.3"',
                 '(blazar OR quasar OR agn OR "active galactic nuclei" OR "3C 454.3")'),
                ('pulsar \'\'neutron star\'\'',
                 '(pulsar OR "neutron star")'),
                ('="planets',
                 '(=planets)'),
                ('"debris disks"\r\n"planet-disk interactions" "zodiacal dust" \r\n"(stars',
                 '("debris disks" OR "planet-disk interactions" OR "zodiacal dust" OR stars)'),
                ('(GONG (or global and oscillation and network and group))',
                 '(GONG OR ("or" OR global AND oscillation AND network AND group))'),
                ('Near Earth Object',
                 '("Near" OR Earth OR Object)'),
                ('(SDO and not subdwarf and not pulsating and \r\nnot pulsational and not pulsate and not pulsation) or HMI or AIA',
                 '((SDO AND NOT subdwarf AND NOT pulsating AND NOT pulsational AND NOT pulsate AND NOT pulsation) OR HMI OR AIA)'),
                ('-redshift \r\n-cosmology \r\n-galaxies\r\n+ISM \r\n+protoplanetary disk\r\n+molecules\r\n+molecular clouds\r\n+comets\r\n+T Tauri\r\n+keplerian disk',
                 '((+ISM OR +protoplanetary OR disk OR +molecules OR +molecular OR clouds OR +comets OR +T OR Tauri OR +keplerian OR disk) AND -redshift AND -cosmology AND -galaxies)'),
                ('AGN\r\nCluster\r\nX-Ray\r\nChandra\r\n"Cygnus A"\r\nMCG 6-30-15\r\n"Black hole"',
                 '(AGN OR Cluster OR X-Ray OR Chandra OR "Cygnus A" OR MCG OR "6-30-15" OR "Black hole")'),
                ('S- Matrix Interpretation of Quantum Theory /Physical Review',
                 '(S OR Matrix OR Interpretation OR of OR Quantum OR Theory OR Physical OR Review)'),
                ('+"XMM-Newton"\r\n+"blackhole accretion"\r\n++gx339-4',
                 '(+"XMM-Newton" OR +"blackhole accretion" OR +gx339-4)'),
            ]:
                output = adsparser.parse_classic_keywords(test)

                self.assertEquals(output, expected)

    #@unittest.skip("only to massively verify impact of changes")
    def test_processed_real_user_input_file(self):
        """
        Test if previously processed user input data are still identical.
        Differences do not necessarily mean something is wrong with the unit test,
        the library could have improved which leads to different results but this
        test will help to identify what queries are affected.

        The processed.txt file was previously generated by the
        test_real_user_input_file_against_solr unit test (solr_success.txt).
        """
        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        with open("adsparser/tests/data/processed.txt", "r") as processed:
            processed_real_cases = processed.readlines()
            for chunk in chunks(processed_real_cases, 4):
                test = chunk[1][10:]
                expected_output = chunk[2][10:][:-1] # Remove \n
                transformed_test = test.replace('\\r', '\r').replace('\\n', '\n')
                output = adsparser.parse_classic_keywords(transformed_test)
                self.assertEquals(output, expected_output)

    @unittest.skip("only for development")
    def test_real_user_input_file(self):
        """
        Process real user input data and control how many fail to be parsed.
        It writes results to 'adsparser/tests/data/tmp/' for manual verification.
        """
        expected_counts = {
            'missing_double_quotes': 0,
            'missing_single_quotes': 0,
            'missing_latex_quotes': 0,
            'missing_parenthesis': 1,
            'empty': 6,
            'success': 12018, # over 12025 (99.94% grammar success rate)
            'unknown': 0,
        }
        if not os.path.isdir("adsparser/tests/data/tmp/"):
            os.makedirs("adsparser/tests/data/tmp/")
        with open("adsparser/tests/data/real.txt", "r") as real, \
                open("adsparser/tests/data/tmp/success.txt", "w") as success, \
                open("adsparser/tests/data/tmp/failure.txt", "w") as failure, \
                open("adsparser/tests/data/tmp/failure_exceptions.txt", "w") as exception:
            real_cases = real.readlines()
            counts = {
                'missing_double_quotes': 0,
                'missing_single_quotes': 0,
                'missing_latex_quotes': 0,
                'missing_parenthesis': 0,
                'empty': 0,
                'success': 0,
                'unknown': 0,
            }
            for test in real_cases:
                transformed_test = test.replace('\\r', '\r').replace('\\n', '\n')
                try:
                    output = adsparser.parse_classic_keywords(transformed_test)
                except Exception, e:
                    if str(e).startswith('No terminal defined for \'"\''):
                        counts['missing_double_quotes'] += 1
                    elif str(e).startswith('No terminal defined for \'\'\''):
                        counts['missing_single_quotes'] += 1
                    elif str(e).startswith('No terminal defined for \'`\''):
                        counts['missing_latex_quotes'] += 1
                    elif str(e).startswith('No terminal defined for \')\'') or str(e).startswith('No terminal defined for \'(\''):
                        counts['missing_parenthesis'] += 1
                    else:
                        failure.write(test)
                        exception.write("--------------------------------------------------------------------------------\n")
                        exception.write(test)
                        exception.write(str(e))
                        counts['unknown'] += 1
                else:
                    if len(output) == 0:
                        counts['empty'] += 1
                    else:
                        counts['success'] += 1
                        success.write("--------------------------------------------------------------------------------\n")
                        success.write(test)
                        success.write(output+"\n")
        for key in counts:
            self.assertEquals(counts[key], expected_counts[key], '[{}] {} != {}'.format(key, counts[key], expected_counts[key]))

    @unittest.skip("only for development")
    def test_real_user_input_file_against_solr(self):
        """
        Process real user input data and send the request to the search endpoint
        to verify it is a valid one.
        It writes results to 'adsparser/tests/data/tmp/' for manual verification.
        """
        search_endpoint = "https://dev.adsabs.harvard.edu/v1/search/query"
        headers = { 'Authorization': 'Bearer {}'.format(os.environ.get('ADS_TOKEN', '<your_token>'))}
        if not os.path.isdir("adsparser/tests/data/tmp/"):
            os.makedirs("adsparser/tests/data/tmp/")
        with open("adsparser/tests/data/solr_failure_source.txt", "r") as real, \
                open("adsparser/tests/data/tmp/solr_success.txt", "w", buffering=0) as success, \
                open("adsparser/tests/data/tmp/solr_failure.txt", "w", buffering=0) as failure, \
                open("adsparser/tests/data/tmp/solr_failure_source.txt", "w", buffering=0) as failure_source:
            real_cases = real.readlines()
            counts = {
                'exception': 0,
                'success': 0,
                'failed_request': 0,
                'empty': 0,
            }
            for test in real_cases:
                transformed_test = test.replace('\\r', '\r').replace('\\n', '\n')
                try:
                    output = adsparser.parse_classic_keywords(transformed_test)
                except Exception, e:
                    counts['exception'] += 1
                else:
                    if len(output) == 0:
                        counts['empty'] += 1
                    else:
                        params = { 'q': output, 'rows': 0}
                        r = requests.get(search_endpoint, params=urlencode(params), headers=headers, timeout=60)
                        failed_request = False
                        if r.status_code == 200:
                            num_found = r.json().get('response', {}).get('numFound', None)
                            if num_found is None:
                                failed_request = True
                        else:
                            failed_request = True

                        if failed_request:
                            counts['failed_request'] += 1
                            failure.write("--------------------------------------------------------------------------------\n")
                            failure.write(test)
                            failure.write(output+"\n")
                            failure_source.write(test)
                        else:
                            success.write("--------------------------------------------------------------------------------\n")
                            success.write("classic.: "+test)
                            success.write("modern..: "+output+"\n")
                            success.write("numFound: {}\n".format(num_found))

