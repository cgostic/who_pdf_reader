# Parses data from WHO monthly risk assessments on Avian flu 
# strains (H5N1, H7N9) into a csv for further analysis
#
# Locates all risk assessment reports (pdf format) format
# https://www.who.int/influenza/human_animal_interface/HAI_Risk_Assessment/en/,
# downloads 1 report at a time to temp folder, extracts data, then deletes
# the download to minimize memory use.
#
# Final CSV exported to results folder
#
# Cari Gostic, January 2nd, 2020
# cari.gostic@gmail.com

import re
import pandas as pd
# Requires PyPDF2
import PyPDF2
# tabula requires java version 1.8.0 or greater. 
# Linux/Mac users can check Java version via the terminal ('java -version' for linux users)
# Windows users may need to set a path to the Java installation
    # See step 2 of https://aegis4048.github.io/parse-pdf-files-while-retaining-structure-with-tabula-py
import tabula
from urllib import request
from bs4 import BeautifulSoup
import os
import urllib
import datetime

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

def download_pdf(download_url, folder):
    """
    Downloads pdf from specified url and saves to specified 
    filepath under filename from URL
    
    Parameters
    ----------
    download_url (str): URL of pdf to download

    folder (str): local filepath in which to save pdf 

    Returns
    -------
    file_path (str): path to downloaded file
    """
    response = urllib.request.urlopen(download_url)
    filename = download_url.split('/')[-1]
    file = open(folder+'/'+filename, 'wb')
    file.write(response.read())
    file.close()
    return(folder+'/'+filename)

def delete_pdf(download_url, folder):
    """
    Deletes pdf that was downloaded from URL to
    a local folder

    Parameters
    ----------
    download_url (str): URL that the pdf was downloaded from

    folder (str): filepath where pdf exists locally
    """
    filename = download_url.split('/')[-1]
    os.remove(folder+'/'+filename)

def convert_date(string):
    """
    Converts date string in format dd/mm/yyyy
    to format dd-Mmm-yyyy
    """
    x = string.split('/')
    #print(x)
    try:
        date = datetime.datetime(int(x[2]),int(x[1]),int(x[0]))
        date_str = date.strftime("%d-%b-%Y")
        return(date_str)
    except (IndexError, ValueError) as errors:
        print('Date formats other than dd/mm/yyyy detected in',report_date,'report:',string)
        pass
###########################################################################

# connect to WHO website and get list of all pdfs
url="https://www.who.int/influenza/human_animal_interface/HAI_Risk_Assessment/en/"
response = request.urlopen(url).read()
soup= BeautifulSoup(response, "html.parser")     
links = soup.find_all('a', href=re.compile(r'(.pdf)'))

# clean the pdf link names
url_list = []
for link in links:
    if(link['href'].startswith('http')):
        url_list.append(link['href'])
    else:
        url_list.append("https://www.who.int" + link['href'])

print(str(len(url_list)), 'pdfs located')
print(url_list[14:24])

# Create temp folder to hold pdfs (one at a time)
folder_location = os.getcwd() + '/tmp_pdfs'
if not os.path.exists(folder_location):os.mkdir(folder_location)

# Create DF to record data in (will be exported as csv)
df = pd.DataFrame(columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure'])

# Loop through files and append information to df
for url in url_list[14:24]:
    file = download_pdf(url, folder_location)  
    pdfFileObj = open(file, 'rb')
    # pdf reader object
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    # number of pages in pdf
    num_pages = pdfReader.numPages
    # extract all text to string
    pageObj = ''
    for i in range(num_pages):
        pageObj = pageObj + pdfReader.getPage(i).extractText()
    pageObj = pageObj.replace('\n', '')

    # Find report date
    if re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj[:300]) != []:
        date_header = re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj[:300])[0].split(' ')
        report_date = date_header[0]+'-'+date_header[1][:3]+'-'+date_header[2]
    else:
        report_date = '...strange report date detected for '+url

    # New infections header string
    ni_header = pageObj[pageObj.find('New infections'):pageObj.find('Risk assessment')]
    # Check for "no new human infections"
    if re.search(r'[Nn]o new human infection', ni_header):
        print('No new cases in',report_date,'report')

    # Check for H5N1 or H7N9 infections
    if not re.search('H5N1', ni_header) and not re.search('H7N9', ni_header):
        print('No cases of H5N1 or H7N9 in',report_date,'report')

    # Check for H5N1 infections
    if re.search('H5N1', ni_header):
        print('Cases of H5N1 detected for',report_date)
    # Check for H7N9 infections
    if re.search('H7N9', ni_header):
        print('Cases of H7N9 Detected for',report_date)
        strain = 'H7N9'
        report_date = report_date
        # Identify paragraph with information on H7N9 infections
        info_start = find_nth(pageObj, 'Avian [Ii]nfluenza A\(H7N9\)', 1)
        info_par = pageObj[info_start:info_start + find_nth(pageObj[info_start:], 
                                'Risk [Aa]ssessment', 1)].replace('\n', '')

        # If annex table exists, extract relevant information to DF
        if re.findall('[Aa]nnex', info_par) != []:
            print('--Annex detected for H7N9 cases in',report_date)
            annex_string = "Annex:[\w* \n:-]*A\(H7N9\)"

            # Find pages with annex table
            for i in range(0, num_pages):
                page_i = pdfReader.getPage(i)
                page_text = page_i.extractText()
                if re.search(annex_string,page_text):
                    annex_page = i
            if annex_page != num_pages:
                i = str(annex_page)+'-'+str(num_pages)
            # pull relevant information from annex table (age, gender, onset date, poultry exposure)
            while True:
                try:
                    print('----Reading data from annex table...')
                    df_annex = tabula.read_pdf(file, lattice=True, pages=i)
                    cols = [x for x in df_annex.columns if not x.startswith('Pro') and not x.startswith('Case')]
                    df_annex = df_annex[cols]
                    df_annex.columns = ['age', 'sex', 'date_onset', 'exposure']
                    break
                except ValueError:
                    print('------Checking if table begins on page after table header...')
                    try:
                        for i in range(0, num_pages):
                            page_i = pdfReader.getPage(i)
                            page_text = page_i.extractText()
                            if re.search(annex_string,page_text):
                                annex_page = i + 1
                        if annex_page != num_pages:
                            i = str(annex_page)+'-'+str(num_pages)
                        df_annex = tabula.read_pdf(file, lattice=True, pages=i)
                        cols = [x for x in df_annex.columns if not x.startswith('Pro') and not x.startswith('Case')]
                        df_annex = df_annex[cols]
                        df_annex.columns = ['age', 'sex', 'date_onset', 'exposure']
                        break
                    except ValueError:
                        print('------Could not read in annex table for '+report_date+'...investigate PDF')
                        break
            # Add strain and report_date columns
            df_annex['strain'] = strain 
            df_annex['date_announced'] = report_date
            # Make poultry exposure binary (0 for no exposure, 1 for exposure)
            df_annex['exposure'] = df_annex['exposure'].str.replace(r'.*[Pp]oultry.*', '1').str.replace(r'[Nn]o [Kk]nown [Ee]xposure', '0').str.replace(r'.*[Ii]nvestig', 'unknown').str.replace(r'[Oo]ccupational [Ee]xposure', '1').str.replace('[Uu]nknow.*', 'unknown').str.replace('[Nn]o clear exposure', '0')
            # Format onset date
            df_annex['date_onset'] =  df_annex['date_onset'].apply(convert_date)
            # Rearrange columns
            df_annex = df_annex[['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure']]
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
                    num_case = '...Check number of cases for '+report_date+' ...could not detect programatically :('
                
            # Identify date of diagnosis/symptoms (no year added)
            if re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
                onset_date_dm = re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
                onset_date = onset_date_dm[0]+'-'+onset_date_dm[1][:3]+'-'+date_header[2]
            elif re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
                onset_date_dm = re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
                onset_date = onset_date_dm[0]+'-'+onset_date_dm[1][:3]+'-'+date_header[2]
            elif re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
                onset_date_dm = re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
                onset_date = onset_date_dm[0]+'-'+onset_date_dm[1][:3]+'-'+date_header[2]
            else:
                if report_date.startswith('weird'):
                    onset_date = 'Report date outside standard format'
                else:
                    onset_date = 'Onset date outside standard format'

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
            df = df.append(pd.DataFrame([[strain, age, gender, onset_date, report_date, poultry_exposure]], 
                                        columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure']))
    delete_pdf(url, folder_location)
df.to_csv('results/WHO-avian-flu-reports_2014-present.csv')

# Delete temp folder
os.removedirs('tmp_pdfs')














# # TEST STRINGS
# st
# Since the last update on 25 January 2018, one laboratory-confirmed human case of influenza A(H7N4) virus infection was reported to WHO. A 68-year-old female resident of Jiangsu province, China, developed symptoms on 25 December 2017.

# st2
# On 11 November 2019, the detection of avian influenza A(H9N2) virus infection in a 4-year-old girl from Fujian province, with an onset of illness on 26 October 2019, was reported to WHO from China. The patient had mild illness but was hospitalized on 5 November 2019. Exposure to backyard poultry was reported. A second case was reported to WHO from China on 23 November, in a 5-year old girl from Anhui province, with an onset of illness on 12 November 2019. The patient had mild illness and recovered. Exposure to a poultry slaughterhouse was reported. No further cases among contacts of the two cases were detected.

# Sample PDFs
#     02_03 1 case H7N9
#     09_27 7 cases H7N9 Annex
#     25_01 1 case H7N9
#     25_11 No H7N9 
#     28_05 No new
#     09_04 1 New H7N9
#     07_25 27 New H7N9 Annex
#     05_16 93 H7N9 Annex 2 pages




# # TO DO

# Check # cases...find H7N9 with 2-3 and try to pull those out of paragraph
# Check if katie wants person-to-person recorded
# Go through her spreadsheet, separate by month, check.
# Add H5N1
# Add loop for multiple cases in a paragraph
    # Look into



# Sources:
    # Read PDF Table
    # https://stackoverflow.com/questions/12571905/finding-on-which-page-a-search-string-is-located-in-a-pdf-document-using-python
    # https://aegis4048.github.io/parse-pdf-files-while-retaining-structure-with-tabula-py

    # Make folder 
    # https://stackoverflow.com/questions/54616638/download-all-pdf-files-from-a-website-using-python

    # Delete folder
    # https://www.dummies.com/programming/python/how-to-delete-a-file-in-python/

    # Download PDF 
    # https://stackoverflow.com/questions/24844729/download-pdf-using-urllib 
    # https://stackoverflow.com/questions/9751197/opening-pdf-urls-with-pypdf
