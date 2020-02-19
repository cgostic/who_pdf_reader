# Helper functions for read_pdf_url.py
# Cari Gostic -- updated Feb 18, 2020

import re
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

bad_dates_rep = []
bad_dates_for = []

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

def month_to_int(mmm):
    """Converts mmm month into respective integer"""
    return{
        'Jan' : '1',
        'Feb' : '2',
        'Mar' : '3',
        'Apr' : '4',
        'May' : '5',
        'Jun' : '6',
        'Jul' : '7',
        'Aug' : '8',
        'Sep' : '9', 
        'Oct' : '10',
        'Nov' : '11',
        'Dec' : '12'
        }[mmm]

def detect_report_date(pageObj):
    """Returns report date from header of WHO assessment report"""
    if re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj) != []:
        date_header = re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj)[0].split(' ')
        report_date = date_header[2]+'-'+month_to_int(date_header[1][:3])+'-'+date_header[0]
    else:
        report_date = 'weird report date detected for '+url
    return(report_date)

def parse_annex_table(num_pages,annex_string, strain, report_date, pdfReader, file):
    """
    Parses annex table in WHO assessment report into pandas dataframe
    with columns strain, age, sex, date_onset, date_announced, exposure.

    Parameters
    ----------
    num pages (int): The number of pages in the pdf

    annex_string (str): String to search for in table header 
    that denotes the start of the annex table for the strain

    strain (str): flu strain

    report_date (str): The WHO assessment report date (dd-Mmm-yyyy)

    Returns
    -------
    DataFrame Object
        A dataframe with columns: 
        strain, age, sex, date_onset, date_announced, exposure
    """
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
            df_annex.columns = ['age', 'sex', 'date_onset', 'poultry_exposure']
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
                df_annex.columns = ['age', 'sex', 'date_onset', 'poultry_exposure']
                break
            except ValueError:
                print('------Could not read in annex table for '+report_date+'...investigate PDF')
                break
    # Add strain and report_date columns
    df_annex['strain'] = strain 
    df_annex['date_announced'] = report_date
    # Make poultry exposure binary (0 for no exposure, 1 for exposure, or unknown if explicitly coded in table)
    df_annex['poultry_exposure'] = (df_annex['poultry_exposure'].str.replace(r'.*[Pp]oultry.*', '1'
        ).str.replace(r'[Nn]o [Kk]nown [Ee]xposure', '0'
        ).str.replace(r'.*[Ii]nvestig', 'unknown'
        ).str.replace(r'[Oo]ccupational [Ee]xposure', '1'
        ).str.replace('[Uu]nknow.*', 'unknown'
        ).str.replace('[Nn]o .*', '0'
        ).str.replace('NR', 'unknown'))
    # Mark human-to-human contact with sick individual
    df_annex['sick_human_exposure'] = (df_annex['poultry_exposure'].str.replace('\d', '0'
        ).str.replace('unknown', '0'
        ).str.replace('.*[A-Za-z].*', '1'))
    df_annex['poultry_exposure'] = df_annex['poultry_exposure'].str.replace(r'.* \w+ \w+.*', '0')
    # Format onset date
    ### report_date now argument -- need to add to "apply call" somehow
    df_annex['date_onset'] =  df_annex['date_onset'].apply(convert_date, report_date = report_date, 
        bad_dates_rep = bad_dates_rep, bad_dates_for = bad_dates_for)
    # Rearrange columns
    df_annex = df_annex[['strain', 'age', 'sex', 
                        'date_onset', 'date_announced', 
                        'poultry_exposure', 'sick_human_exposure']]
    return(df_annex)

def detect_patient_age(info_par):
    """Returns age of patient described in paragraph of WHO assessment"""
    # Searches for "year-old" or 'year old'
    if re.findall('(\d{1,2}) ?(:?-?(year|month)(-| )old)',info_par) != []:
        age = re.findall('(\d{1,2}) ?(:?-?(year|month)(-| )old)',info_par)[0][0]
    else:
        age = 'unknown'
    return(age)

def detect_onset_date(pageObj,info_par, report_date):
    """Returns the illness onset date as described in paragraph of WHO assessment"""
    # Seaches for date in sentence with "symptoms", "developed", or "onset"
    date_header = re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj)[0].split(' ')
    if re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
        onset_date_dm = re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
        onset_date = date_header[2]+'-'+month_to_int(onset_date_dm[1][:3])+'-'+onset_date_dm[0]
    elif re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
        onset_date_dm = re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
        onset_date = date_header[2]+'-'+month_to_int(onset_date_dm[1][:3])+'-'+onset_date_dm[0]
    elif re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
        onset_date_dm = re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
        onset_date = date_header[2]+'-'+month_to_int(onset_date_dm[1][:3])+'-'+onset_date_dm[0]
    else:
        if report_date.startswith('weird'):
            onset_date = 'bad report date'
        else:
            onset_date = 'check onset date format for '+url
    return(onset_date)

def detect_patient_gender(info_par):
    """Returns the age of patient described in WHO assessment"""
    # Look for either MALE or FEMALE, or in case where
    # gender is not explicitly stated, search for pronouns
    if re.findall('(male|female)', info_par) != []:
        gender = re.findall('(male|female)', info_par)[0][0]
    elif re.findall('( [Hh]e | [Hh]er )', info_par) != []:
        gender = re.findall('( [Hh]e | [Ss]he )', info_par)[0]
        if gender == ' he ' or gender == ' He ':
            gender = 'm'
        else:
            gender = 'f'
    elif re.findall('( [Mm]an | [Ww]oman )', info_par) != []:
        gender = re.findall('( [Mm]an | [Ww]oman )', info_par)[0]
        if gender == ' man ' or gender == ' Man ':
            gender = 'm'
        else:
            gender = 'f'
    else:
        gender = 'Not reported as male/female...Check '+url
    return(gender)

def detect_poultry_exposure(info_par):
    """
    Returns poultry exposure (binary, 0 = no exposure, 1 = exposure) as described
    in WHO assessment report
    """
    if re.findall('(?<=\.)( [A-Za-z ,]* poultry [A-Za-z ,]*)(\.|;)',info_par) != []:
        poul_sentence = re.findall('((?<=\.)( [A-Za-z ,]* poultry [A-Za-z ,]*)(\.|;))',info_par)[0][0]
    elif re.findall('(\w* )*(exposure )(\w* )*', info_par) != []:
        poul_sentence = re.findall('((\w* )*(exposure )(\w* )*)', info_par)[0][0]
    elif re.findall('(\w* )*(birds? )(\w* )*', info_par) != []:
        poul_sentence = re.findall('((\w* )*(birds? )(\w* )*)', info_par)[0][0]
    # Code exposure as binary 1 = exposure, 0 = no exposure
    if not re.search('([Nn]o |not|none)', poul_sentence):
        poultry_exposure = 1
        sick_human_exposure = 0
    else:
        poultry_exposure = 0
        sick_human_exposure = 0
    return(poultry_exposure, sick_human_exposure)

def convert_date(string, report_date, bad_dates_rep, bad_dates_for):
    """
    Converts date string in format dd/mm/yyyy
    to format dd-Mmm-yyyy
    """
    x = string.split('/')
    try:
        date = datetime.datetime(int(x[2]),int(x[1]),int(x[0]))
        date_str = date.strftime("%Y-%m-%d")
        return(date_str)
    # Print out cases that do not match input date convention 
    except (IndexError, ValueError) as errors:
        bad_dates_rep.append(report_date)
        bad_dates_for.append(string)
        return(string)
        pass

