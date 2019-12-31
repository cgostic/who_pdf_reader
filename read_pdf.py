import PyPDF2
import re
import pandas as pd

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

# Create DF to record data in
df = pd.DataFrame(columns = ['strain', 'onset_date', 'poultry_exposure', 'age'])


# pdf file object
# you can find find the pdf file with complete code in below
pdfFileObj = open('pdfs/Influenza_Summary_IRA_HA_interface_02_03_2018.pdf', 'rb')
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
    print('No new cases in INSERT DATE report')

# Check for H5N1 or H7N9 infections
elif not re.search('H5N1', ni_header) and not re.search('H7N9', ni_header):
    print('No cases of H5N1 or H7N9 in INSERT DATE report')

# Check for H5N1 infections
elif re.search('H5N1', ni_header):
    pass
# Check for H7N9 infections
elif re.search('H7N9', ni_header):
    strain = 'H7N9'
    # Identify paragraph with information on H7N9 infections
    info_start = find_nth(pageObj, 'Avian [Ii]nfluenza A\(H7N9\)', 1)
    info_par = pageObj[info_start:info_start + find_nth(pageObj[info_start:], 
                        'Risk [Aa]ssessment', 1)].replace('\n', '')
        
    # Identify date of diagnosis/symptoms (no year added)
    if re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != []:
        onset_date = re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)', 
                info_par)[0][-1]
    if re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != []:
        onset_date = re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)', 
                info_par)[0][-1]

    # Identify age -- if multiple, change first index from 0 to 1 to get second age
    age = re.findall('(\d{1,2})(:?-?(year|month)(-| )old)', 
            info_par)[0][0]

    # Check for poultry exposure
    poul_sentence = re.findall('(?<=\.)( [A-Za-z ,]* poultry [A-Za-z ,]*)(\.|;)', 
            info_par)[0][0]
    if not re.search('(no|not)', poul_sentence):
        poultry_exposure = 1
    else:
        poultry_exposure = 0

    # # Identify number of new infections in reporting period
    # if re.find('\w*(?= laboratory-confirmed)', info_par)[0] == 'new':
    #     num_case = re.findall('\w*(?= new laboratory-confirmed)', info_par)[0]
    # else:
    #     num_case = re.findall('\w*(?= laboratory-confirmed)', info_par)[0]

# Add values to data frame
df = df.append(pd.DataFrame([[strain, onset_date, poultry_exposure, age]], 
                            columns = ['strain', 'onset_date', 'poultry_exposure', 'age']))
print(df)














## TEST STRINGS
# st
#Since the last update on 25 January 2018, one laboratory-confirmed human case of influenza A(H7N4) virus infection was reported to WHO. A 68-year-old female resident of Jiangsu province, China, developed symptoms on 25 December 2017.

# st2
#On 11 November 2019, the detection of avian influenza A(H9N2) virus infection in a 4-year-old girl from Fujian province, with an onset of illness on 26 October 2019, was reported to WHO from China. The patient had mild illness but was hospitalized on 5 November 2019. Exposure to backyard poultry was reported. A second case was reported to WHO from China on 23 November, in a 5-year old girl from Anhui province, with an onset of illness on 12 November 2019. The patient had mild illness and recovered. Exposure to a poultry slaughterhouse was reported. No further cases among contacts of the two cases were detected.


## TO DO

# Date of onset                   done -- need to get year from report date
# Date reported?                              
# Each case in separate line      use if or add annex!!!
# age                             done
# contact with poultry            done
# type of strain                  done

# Add loop for multiple cases in a paragraph
# Add read-in of annex if exists
# Check other documents
# Access pdfs programatically!