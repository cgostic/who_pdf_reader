import re
import pandas as pd
# Requires PyPDF2
import PyPDF2
# tabula requires java version 1.8.0 or greater. 
# Linux/Mac users can check Java version via the terminal ('java -version' for linux users)
# Windows users may need to set a path to the Java installation
    # See step 2 of https://aegis4048.github.io/parse-pdf-files-while-retaining-structure-with-tabula-py
import tabula

##########################################################
# PDF Files
##########################################################
files = ['pdfs/Influenza_Summary_IRA_HA_interface_09_27_2017.pdf',
        'pdfs/Influenza_Summary_IRA_HA_interface_02_03_2018.pdf',
        'pdfs/Influenza_Summary_IRA_HA_interface_05_16_2017.pdf',
        'pdfs/Influenza_Summary_IRA_HA_interface_07_25_2017.pdf',
        'pdfs/Influenza_Summary_IRA_HA_interface_09_04_2019.pdf']



###########################################################
# FUNCTIONS
###########################################################
def find_nth(haystack, needle, n):
    """
    Finds nth occurrence of a string in a piece of text.
    If n is negative, returns nth instance of string from
    the end of the text.

    Parameters
    ----------
    haystack (str): piece of text to search through

    needle (str): string to search for in text

    n (int): which occurence to identify (1st, 2nd, 3rd)

    Returns:
    -------
    int:
        position in haystack where nth occurrence of
        needle starts.
    """
    if n < 0:
        return [match.start(0) for match in re.finditer(needle, haystack)][n]
    else:
        return [match.start(0) for match in re.finditer(needle, haystack)][n-1]
##############################################################################################

# Create DF to record data in (will be exported as csv)
df = pd.DataFrame(columns = ['strain', 'onset_date', 'report_date', 'age', 'gender', 'poultry_exposure'])

# Loop through files and append information to df
for file in files:
    report_date_str = re.findall('\d\d_\d\d_\d\d\d\d', file)[0]
    pdfFileObj = open(file, 'rb')
    # pdf reader object
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    # number of pages in pdf
    num_pages = pdfReader.numPages
    # a page object
    pageObj = ''
    for i in range(num_pages):
        pageObj = pageObj + pdfReader.getPage(i).extractText()

    # New infections header string
    ni_header = pageObj[pageObj.find('New infections'):pageObj.find('Risk assessment')]

    # Check for "no new human infections"
    if re.search(r'[Nn]o new human infection', ni_header):
        print('No new cases in',report_date_str,'report')

    # Check for H5N1 or H7N9 infections
    if not re.search('H5N1', ni_header) and not re.search('H7N9', ni_header):
        print('No cases of H5N1 or H7N9 in',report_date_str,'report')

    # Check for H5N1 infections
    if re.search('H5N1', ni_header):
        print('Cases of H5N1 detected for',report_date_str)
    # Check for H7N9 infections
    if re.search('H7N9', ni_header):
        print('Cases of H7N9 Detected for',report_date_str)
        strain = 'H7N9'
        report_date = report_date_str
        # Identify paragraph with information on H7N9 infections
        info_start = find_nth(pageObj, 'Avian [Ii]nfluenza A\(H7N9\)', 1)
        info_par = pageObj[info_start:info_start + find_nth(pageObj[info_start:], 
                                'Risk [Aa]ssessment', 1)].replace('\n', '')

        # If annex table exists, extract relevant information to DF
        if re.findall('[Aa]nnex', info_par) != []:
            print('Annex detected for H7N9 cases in',report_date_str)
            annex_string = "Annex:[\w* \n:-]*A\(H7N9\)"

            # Find pages with annex table
            for i in range(0, num_pages):
                page_i = pdfReader.getPage(i)
                page_text = page_i.extractText()
                if re.search(annex_string,page_text):
                    annex_page = i
            if i != num_pages:
                i = str(i)+','+str(num_pages)
            # pull relevant information from annex table (age, gender, onset date, poultry exposure)
            df_annex = tabula.read_pdf(file, lattice=True, pages=i, pandas_options={'usecols' : ['Age', 'Sex', 'Date of onset\r(dd/mm/yyyy)', 'Exposure history (at time of reporting)']})
            df_annex.columns = ['age', 'gender', 'onset_date', 'poultry_exposure']
            # Add strain and report_date columns
            df_annex['strain'] = strain 
            df_annex['report_date'] = report_date
            # Make poultry exposure binary (0 for no exposure, 1 for exposure)
            df_annex['poultry_exposure'] = df_annex['poultry_exposure'].str.replace(r'.*poultry.*', '1').str.replace(r'[Nn]o [Kk]nown [Ee]xposure', '0')
            # Rearrange columns
            df_annex = df_annex[['strain', 'onset_date', 'report_date', 'age', 'gender', 'poultry_exposure']]
            df = df.append(df_annex)
        # If no annex table exists, extract information from paragraph
        # describing H7N9 cases
        else:
            # Identify number of new infections in reporting period
            if re.findall('\w*(?= laboratory-confirmed)', info_par)[0] == 'new':
                num_case = re.findall('\w*(?= new laboratory-confirmed)', info_par)[0].replace(' ', '')
            else:
                num_case = re.findall('\w*(?= laboratory-confirmed)', info_par)[0].replace(' ', '')
            # If reported number is string, convert to integer
            if not str.isdigit(num_case):
                if num_case == 'one':
                    num_case = 1
                elif num_case == 'two':
                    num_case = 2
                elif num_case == 'three':
                    num_case = 3
                elif num_case == 'four':
                    num_case = 4
                elif num_case == 'five':
                    num_case = 5
                elif num_case == 'six':
                    num_case = 6 
                else:
                    num_case = 'Check number of cases for '+report_date_str
                
            # Identify date of diagnosis/symptoms (no year added)
            if re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != []:
                onset_date = re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1]
            if re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != []:
                onset_date = re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1]
            if re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)', info_par) != []:
                onset_date = re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1]

            # Identify age -- if multiple, change first index from 0 to 1 to get second age
            age = re.findall('(\d{1,2})(:?-?(year|month)(-| )old)',info_par)[0][0]
            
            # Identify gender
            gender = re.findall('(male|female)', info_par)[0][0]
            
            # Check for poultry exposure
            if re.findall('(?<=\.)( [A-Za-z ,]* poultry [A-Za-z ,]*)(\.|;)',info_par) != []:
                poul_sentence = re.findall('((?<=\.)( [A-Za-z ,]* poultry [A-Za-z ,]*)(\.|;))',info_par)[0][0]
            elif re.findall('(\w* )*(exposure )(\w* )*', info_par) != []:
                poul_sentence = re.findall('((\w* )*(exposure )(\w* )*)', info_par)[0][0]
            if not re.search('(no|not|none)', poul_sentence):
                poultry_exposure = 1
            else:
                poultry_exposure = 0

            # Add values to data frame
            # columns = ['strain', 'onset_date', 'report_date', 'poultry_exposure', 'age' 'gender']
            df = df.append(pd.DataFrame([[strain, onset_date, report_date, age, gender, poultry_exposure]], 
                                        columns = ['strain', 'onset_date', 'report_date', 'age', 'gender', 'poultry_exposure']))
print(df)














## TEST STRINGS
# st
#Since the last update on 25 January 2018, one laboratory-confirmed human case of influenza A(H7N4) virus infection was reported to WHO. A 68-year-old female resident of Jiangsu province, China, developed symptoms on 25 December 2017.

# st2
#On 11 November 2019, the detection of avian influenza A(H9N2) virus infection in a 4-year-old girl from Fujian province, with an onset of illness on 26 October 2019, was reported to WHO from China. The patient had mild illness but was hospitalized on 5 November 2019. Exposure to backyard poultry was reported. A second case was reported to WHO from China on 23 November, in a 5-year old girl from Anhui province, with an onset of illness on 12 November 2019. The patient had mild illness and recovered. Exposure to a poultry slaughterhouse was reported. No further cases among contacts of the two cases were detected.

# Sample PDFs
    # 02_03 1 case H7N9
    # 09_27 7 cases H7N9 Annex
    # 25_01 1 case H7N9
    # 25_11 No H7N9 
    # 28_05 No new
    # 09_04 1 New H7N9
    # 07_25 27 New H7N9 Annex
    # 05_16 93 H7N9 Annex 2 pages




## TO DO

# Columns
    # Date of onset                   done -- need to get year from report date
    # Date reported?                  update after read-in from WHO site           
    # Each case in separate line      done
    # age                             done
    # contact with poultry            done
    # type of strain                  done
    # Gender                          done

# Check test cases for accuracy
# Update date format for non-annex
# update date format for report_date
# Add loop for multiple cases in a paragraph
    # Look into
# Access pdfs programatically!
# check with katie for date formats, columns names, column orders, etc.


# Sources:
    # Read PDF Table
    # https://stackoverflow.com/questions/12571905/finding-on-which-page-a-search-string-is-located-in-a-pdf-document-using-python
    # https://aegis4048.github.io/parse-pdf-files-while-retaining-structure-with-tabula-py
