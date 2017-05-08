import re
import nltk
import requests
from bs4 import BeautifulSoup
import os
import os.path
import string

# url parsed is "http://appft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&u=%2Fnetahtml%2FPTO%2Fsearch-
# adv.html&r=0&p=1&f=S&l=50&Query=aanm%2F%22carnegie+mellon%22+AND+PD%2F4%2F1%2F2016-%3E6%2F30%2F2016&d=PG01"
baseurl = "http://appft.uspto.gov/"
URL = "http://appft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&u=%2Fnetahtml%2FPTO%2Fsearch" \
      "-adv.html&r=0&p=1&f=S&l=50&Query=aanm%2F%22carnegie+mellon%22+AND+PD%2F4%2F1%2F2016-%3E6%2F30%2F2016&d=PG01"
alpha=string.ascii_lowercase

def loadStopwords(file):
    from nltk.corpus import stopwords
    stop = set(stopwords.words('english'))   # load the stopwords in the nltk corpus to filter unnecessary keywords
    f = open(file)
    stopwords = [line.strip() for line in f.readlines()] # load stopwords in our given file
    f.close()
    return set(stopwords) | stop   # combine them the two sets of stopwords


def loadSubwords(file):
    d = {}
    with open(file, encoding='latin1') as f:
        for line in f:
            line=line.strip()
            if len(line)>0:
                wrong, correct = line.strip().split(',')
                d[wrong] = correct
    return d      # load words for replacement into a dictionary


def extract_html(link):
    content = requests.get(baseurl + link).text  # extract the html based a given url
    return content


def process(word_list, stopwords, subwords):

    func = lambda x : x.strip() and x.isalpha() and x not in stopwords

    l = list(filter(func, map(str.lower, word_list))) # pick out alphabet words that are not in the stopwords
    for i, word in enumerate(l):
        if word in subwords:
            l[i] = subwords[word] # replace them

    return set(l)


def writeHTML(keywords):
    # create a html file including all the keywords
    GEN_HTML = "index1.html"

    message = """
    <!doctype html>
    <html>
    <head>
    <meta charset="UTF-8">
    <title>INDEX</title>
    <style type="text/css">
        * {padding:0; margin:0;}
        a {text-decoration:none;}
        li {list-style:none:}
        /* Navigation STyling */
        .main-nav {width: 250px; background: rgba(180,205,203,1.00);}
        .main-nav a {
            text-transform: uppercase;
            letter-spacing: .2em;
            color: #FFF;
            display: block;
            padding: 10px 0 10px 20px;
            border-bottom: 1px dotted gray;
        }
        .main-nav a:hover {background: rgba(121,165,162,1.00);}
        .main-nav-ul ul {display:none;}
        .main-nav-ul li:hover ul {display: block;}
        
        .main-nav-ul ul a:before { content:'\\203A'; margin-right: 20px;}
        .main-nav .sub-arrow:after {
        content: '\\203A';
        float: right;
        margin-right: 20px;
        transform: rotate(90deg);
        -webkit-transform: rotate(90deg);
        -moz-transform: rotate(90deg);
        }
        .main-nav li:hover .sub-arrow:after{content: '\\2039';}
    </style>
    </head>
    <body>
    <p><font size="7"><b>U.S.Patent Library</b></font></p>
    <p><font size="5"><b>You can search the patent library by the following key words</b></font></p>
    <nav class="main-nav">
    <ul class="main-nav-ul">"""
    for a in alpha:
        message+='<li><a href="#">%s<span class="sub-arrow"></span></a>'% (a)
        message+='<ul>'
        for word in sorted(keywords):
            if word.startswith(a):
                message +=  """<li><a href="%s"><font size="4">"""% (keywords[word].getPath()) + word.capitalize()\
                            + """</font></a></li>"""
        message+='</ul></li>'

    message += "</ul>"
    message += """</nav><p><font size="4">Author: Tony Tian</font></p>"""
    message += """</body></html>"""
    f = open(GEN_HTML,'w')
    f.write(message)
    f.close()


class Keyword(object):

    def __init__(self, k):
        self.word = k
        self.person = False      # initiate with given word, and include two attributes indicating its features
        self.applications = set()  # store applications that include this word

    def generate(self, keywords):
    # generate sub html pages
        word = self.word
        filepath = self.getPath()

        if not os.path.exists("keywords/"):
            os.mkdir("keywords/")

        with open(filepath, 'w') as f:
            message = "<html>\n<head></head>\n<body>\n"

            if not self.person:
                message += "<p><font size=\"5\"><b>Keyword : %s </b></font></p>\n" % word.capitalize()
                message += "<p><font size=\"4\"><b>This keyword is found in the following applications</b></font></p>\n"

                for i, app in enumerate(self.applications):
                    tt = ['<a href="%s">'% (keywords[t.lower()].getPath().replace("keywords/","")) + t + "</a>"
                          for t in app.inventors]
                    message += "<p> %d %s by (%s)</p>\n" % (i+1, app.name, ",".join(tt))
                    message += "<p>" + app.abstract + "</p>"
                    message += "\n"
                message += "</body></html>\n"
            else:
                message += "<p><font size=\"5\"><b>Person : %s </b></font></p>\n" % word.capitalize()
                message += "<p><font size=\"4\"><b>This Person has invented the following applications</b></font></p>\n"

                for i, app in enumerate(self.applications):
                    message += "%d %s \n\n" % (i+1, app.name)
                    message += "<p>" + app.abstract + "</p>"
                    message += "\n"
                message += "</body></html>\n"

            f.write(message)

    def getPath(self):
        return 'keywords/%s.html' % self.word # return the path created for the word


class Application(object):
    # extract key parts from applications' texts and store them
    def __init__(self, content):
        self.content = content

    def extract(self, stopwords, subwords, keywords):
        soup = BeautifulSoup(self.content, "html.parser")
        self.name = soup.find_all("font",size="+1")[0].get_text().strip().upper()
        text=soup.find_all(text=True)[1:]
        text = list(filter(lambda x: "<AANM>" not in x and "Times New Roman" not in x ,text))
        self.text="".join(text).strip()
        idx = self.text.find('Inventors:')
        idx2 = self.text.find('Applicant:')
        idx3 = self.text.find('Abstract')

        self.abstract = self.text[idx3:idx].strip()

        inventors = self.text[idx:idx2]
        inventors = re.sub(r'\(.*?\)', '', inventors)
        inventors = inventors.split(':')[1].split(';')

        self.inventors = list(filter(lambda x : x, map(str.strip, inventors)))

        word_list = nltk.word_tokenize(self.text)

        self.keywords = process(word_list, stopwords, subwords)

        for inv in self.inventors:
            word = inv.lower()
            if word not in keywords:
                keywords[word] = Keyword(inv)

            keywords[word].person = True
            keywords[word].applications.add(self)

        for word in self.keywords:
            word= word.lower()
            if word not in keywords:
                keywords[word] = Keyword(word)
            keywords[word].applications.add(self)


if __name__ == "__main__":

    keywords = {}

    stopwords = loadStopwords('Milestone_stop.txt')
    subwords = loadSubwords('Milestone_replace.csv')

    # load search results
    html = requests.get(URL).text
    soup = BeautifulSoup(html, 'html5lib')

    # extract links from search results
    links = set()
    for g in soup.body.table.tbody.select('a'):
        links.add(g['href'])

    # extract keywords from links
    apps=[]
    for link in links:
        text = extract_html(link)
        apps.append(Application(text))

    for app in apps:
        app.extract(stopwords, subwords, keywords)


    for word in keywords:
        keywords[word].generate(keywords)

    writeHTML(keywords)