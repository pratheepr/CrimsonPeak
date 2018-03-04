import os
from tika import parser
import pytesseract
from PIL import Image
import re
import shutil
from nltk import wordpunct_tokenize
from nltk.corpus import stopwords
from elasticsearch import helpers, Elasticsearch
import os

os.environ['PYTHONIOENCODING'] = 'utf8'

doc_document_name = ' '
doc_document_create_Date = ''
doc_author = ' '
doc_title = ' '
doc_content = ' '
doc_text_data = ' '
newlist = []
doc_title = ' '

ES_HOST = {"host": "localhost", "port": 9200}

INDEX_NAME = 'ocr_b2b2018'
TYPE_NAME = 'docx'


def _calculate_languages_ratios(text):
    languages_ratios = {}

    tokens = wordpunct_tokenize(text)
    words = [word.lower() for word in tokens]

    # Compute per language included in nltk number of unique stopwords appearing in analyzed text
    for language in stopwords.fileids():
        stopwords_set = set(stopwords.words(language))
        words_set = set(words)
        common_elements = words_set.intersection(stopwords_set)

        languages_ratios[language] = len(common_elements)  # language "score"

    return languages_ratios


def detect_language(text):
    ratios = _calculate_languages_ratios(text)

    #   print(ratios)

    most_rated_language = max(ratios, key=ratios.get)

    # return most_rated_language
    return ratios


#### Remove special and non-ascii characters #######
def strings_remove_non_ascii(input_string):
    tmp_str = ''
    try:
        tmp_str = (re.sub('\s+', ' ', input_string).strip()).encode('ascii', errors='ignore').decode()
    except:
        tmp_str = input_string
    return (tmp_str)


def tika_parser(file_name):
    global doc_title,doc_last_author, doc_text_data, doc_author, doc_document_name, doc_document_create_Date
    tika_text_ascii = ' '
    tessaract_output = ' '
    s = {}
    re_auth = ''
    re_unser_zeichen = ''

    try:
        parsed_text = parser.from_file(file_name)
        #   print(parsed_text["metadata"])

        doc_metadata = parsed_text["metadata"]

        if "Author" in doc_metadata.keys():
            doc_author = doc_metadata["Author"]
        else:
            doc_author = ' '

        if "Last-Author" in doc_metadata.keys():
            doc_last_author = ' ' + doc_metadata["Last-Author"]
        else:
            doc_last_author = ' '

        if "Creation-Date" in doc_metadata.keys():
            doc_document_create_Date = doc_metadata["Creation-Date"]
        else:
            doc_document_create_Date = ' '

        if (len(doc_document_create_Date) == 2):
            doc_document_create_Date = doc_document_create_Date[0]

        # doc_title = parsed_text["metadata"]["title"]
        doc_title = file_name

        print(' Document Metadata *****')
        print(doc_title + ' ' + doc_author + doc_last_author + ' ' + str(doc_document_create_Date) + ' ')

        # print(parsed_text["content"])
        # tika_text = re.sub('\s+', ' ', parsed_text["content"]).strip()
        tika_text_ascii = strings_remove_non_ascii(parsed_text["content"])
        print('tika_text_ascii is' + tika_text_ascii)

        s['doc_title'] = doc_title.lower()
        s['doc_author'] = doc_author.lower() + doc_last_author.lower()
        s['doc_create_date'] = str(doc_document_create_Date)

    except:
        print('Errors in parsing file  by Tika parser: ' + file_name)

    if tika_text_ascii == 'None' or tika_text_ascii == '' or tika_text_ascii is None or len(tika_text_ascii) < 150:
        tessaract_output = tessaract_parser(filename)
        print(' testing only')

    doc_text_data = str(tika_text_ascii) + tessaract_output

    doc_text_clean = re.sub('[^a-zA-Z0-9 \n\.]', '', doc_text_data).lower()

    # print(doc_text_clean)


    s['doc_text'] = doc_text_data
    s['doc_text_clean'] = doc_text_clean
    s['doc_title_clean'] = re.sub('[^a-zA-Z0-9 \n\.]', ' ', doc_title).lower()

    try:
        author_from = re.findall('autor *: *[a-z ]*', doc_text_data)[0]
        print(author_from)
        re_auth = re.sub('^:?[a-z]*', '', author_from)

        unser_zeichen = re.findall('unser zeichen *: *[0-9.]* ?', doc_text_data)[0]
        re_unser_zeichen = re.sub('^:?[0-9.]*', '', unser_zeichen)

    except:
        print('passing along')

    s['doc_meta_author'] = re_auth
    s['doc_meta_zeichen'] = re_unser_zeichen

    newlist.append(s)


def tessaract_parser(file_name):
    # os.chdir('/Users/pratheepravysandirane/PycharmProjects/Python_OCR')
    tessaract_return_string = ''

    command_string = 'pdfimages -png ' + file_name + ' ' + rootdir + '/tmp/img'

    print('inside tessaract parser')
    # os.system('pdfimages -png Neuendorf.pdf Neuimg')

    os.system(command_string)

    for subdir, dirs, files in os.walk(rootdir + '/tmp'):
        for file in files:
            filename = os.path.join(subdir, file)
            print('Tesseract processing')
            print(filename)

            tmp_img = Image.open(filename)

            print('OCR processing 0')
            tessaract_string_base = pytesseract.image_to_string(tmp_img)
            print('width: %d - height: %d' % tmp_img.size)

            width, height = tmp_img.size

            new_size = height, width
            # dst_im = Image.new("RGBA")
            # dst_im.save( "00-" + filename )

            print('OCR processing 90')
            tessaract_string_90d = pytesseract.image_to_string(tmp_img.rotate(90, expand=1).resize(new_size))
        #    print('width: %d - height: %d' % tmp_img.rotate(90).size)
            # dst_im.save( "90-" + filename )

            print('OCR processing 180')
            tessaract_string_180d = pytesseract.image_to_string(tmp_img.rotate(180))
       #     print('width: %d - height: %d' % tmp_img.rotate(180).size)

            print('OCR processing 270')
            tessaract_string_270d = pytesseract.image_to_string(tmp_img.rotate(270, expand = 1).resize(new_size))
        #    print('width: %d - height: %d' % tmp_img.rotate(270).size)

            print('Completed Tessaract Processing')

            #            P = pytesseract.image_to_string(img.rotate(90))
            tessaract_OCR_String = strings_remove_non_ascii(tessaract_string_base)
            tessaract_OCR_String_90d = strings_remove_non_ascii(tessaract_string_90d)
            tessaract_OCR_String_180d = strings_remove_non_ascii(tessaract_string_180d)
            tessaract_OCR_String_270d = strings_remove_non_ascii(tessaract_string_270d)

            lang_score_0 = detect_language(tessaract_OCR_String)
            lang_score_90 = detect_language(tessaract_OCR_String_90d)
            lang_score_180 = detect_language(tessaract_OCR_String_180d)
            lang_score_270 = detect_language(tessaract_OCR_String_270d)

            text_english_score = lang_score_0['english'] + lang_score_90['english'] + lang_score_180['english'] + \
                                 lang_score_270['english']
            text_german_score = lang_score_0['german'] + lang_score_90['german'] + lang_score_180['german'] + \
                                lang_score_270['german']
            text_french_score = lang_score_0['french'] + lang_score_90['french'] + lang_score_180['french'] + \
                                lang_score_270['french']
            text_italian_score = lang_score_0['italian'] + lang_score_90['italian'] + lang_score_180['italian'] + \
                                 lang_score_270['italian']

            if text_english_score > text_german_score and text_english_score > text_german_score and text_english_score > text_italian_score:
                doc_lang = 'english'

            if text_german_score > text_english_score and text_german_score > text_french_score and text_german_score > text_italian_score:
                doc_lang = 'german'

            if text_french_score > text_english_score and text_french_score > text_german_score and text_french_score > text_italian_score:
                doc_lang = 'french'

            if text_italian_score > text_english_score and text_italian_score > text_german_score and text_italian_score > text_french_score:
                doc_lang = 'italian'

            text_0_lang = max(lang_score_0, key=lang_score_0.get)
            text_90_lang = max(lang_score_90, key=lang_score_90.get)
            text_180_lang = max(lang_score_180, key=lang_score_180.get)
            text_270_lang = max(lang_score_270, key=lang_score_270.get)

            OCR_output_string = ''

            if doc_lang == text_0_lang:
                OCR_output_string = tessaract_OCR_String
            elif doc_lang == text_90_lang:
                OCR_output_string = tessaract_OCR_String_90d
            elif doc_lang == text_180_lang:
                OCR_output_string = tessaract_OCR_String_180d
            elif doc_lang == text_270_lang:
                OCR_output_string = tessaract_OCR_String_270d
            else:
                OCR_output_string = ''

            # print('Tessaract 0 Degrees: ')
            # print(tessaract_OCR_String)
            # print('Tessaract 90 Degrees: ')
            # print(tessaract_OCR_String_90d)
            # print('Tessaract 180 Degrees: ')
            # print(tessaract_OCR_String_180d)
            # print('Tessaract 270 Degrees: ')
            # print(tessaract_OCR_String_270d)

            print('Tesseract Ending')

            # print(' CALCULATED TEXT OUTPUT :')
            # print(OCR_output_string)

            tessaract_return_string = (
                        tessaract_return_string + tessaract_OCR_String + tessaract_OCR_String_90d + tessaract_OCR_String_180d + tessaract_OCR_String_270d).lower()

            # print(tessaract_return_string)
            # print('Author is : ')
            # author_from = re.findall('autor *: *[a-z ]*', tessaract_return_string)[0]
            # print('author every page : ')
            # print(author_from)
            # re_auth = re.sub('^:?[a-z]*', '',author_from)
            # print(re_auth)

    shutil.rmtree(rootdir + '/tmp/')
    os.mkdir(rootdir + '/tmp/')

    return tessaract_return_string


# os.remove(rootdir+'/tmp/')

# print(parsed["metadata"]
# print(P)

# Loop thru directory

def Init_Elasticsearch():
    es = Elasticsearch(
        ['localhost'],
        http_auth=('elastic', 'changeme'),
        port=9200,
        use_ssl=False
    )

    if es.indices.exists(INDEX_NAME):
        print("deleting '%s' index..." % (INDEX_NAME))
        res = es.indices.delete(index=INDEX_NAME)
        print(" response: '%s'" % (res))

    print("creating '%s' index..." % (INDEX_NAME))
    res = es.indices.create(index=INDEX_NAME)  # , body= cust_univ_mapping)
    print(" response: '%s'" % (res))

    return es


es = Init_Elasticsearch()

rootdir = '/Users/pratheepravysandirane/Downloads/testDocs/'

# make an empty dict to store new dict data
counter = 1

for subdir, dirs, files in os.walk(rootdir):
    for file in files:
        filename = os.path.join(subdir, file)
        print(filename)
        if filename.endswith('.xlsm') or filename.endswith('.docx'):
            doc_document_name = filename
            tika_parser(filename)
            print(' ')
        if filename.endswith('.pdf'):
            doc_document_name = filename
            tika_parser(filename)
            print(' ')

print("Indexing Started...")

helpers.bulk(es, newlist, index=INDEX_NAME, doc_type=TYPE_NAME)
# helpers.bulk(es, reader, index=INDEX_NAME, doc_type=TYPE_NAME)

print("completed creating Index")
