import requests
import requests.sessions
import re
import sys
import os

class Session:
	"""Starting session with proper headers to access udemy site"""
	headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:39.0) Gecko/20100101 Firefox/39.0',
			   'X-Requested-With': 'XMLHttpRequest',
			   'Host': 'www.udemy.com',
			   'Referer': 'https://www.udemy.com/join/login-popup'}

	def __init__(self):
		self.session = requests.sessions.Session()
		
	def set_auth_headers(self, access_token, client_id):
		""" Setting up authentication headers. """
		self.headers['X-Udemy-Bearer-Token'] = access_token
		self.headers['X-Udemy-Client-Id'] = client_id
		self.headers['Authorization'] = "Bearer " + access_token
		self.headers['X-Udemy-Authorization'] = "Bearer " + access_token

	def get(self, url):
		""" Retreiving content of a given url. """
		return self.session.get(url, headers=self.headers)

	def post(self, url, data):
		""" HTTP post given data with requests object. """
		return self.session.post(url, data, headers=self.headers)

session = Session()

def get_csrf_token():
	""" Extractig CSRF Token from login page """
	response = session.get('https://www.udemy.com/join/login-popup')
	match = re.search("name=\'csrfmiddlewaretoken\' value=\'(.*)\'", response.text)
	return match.group(1)

def get_course_id(course_link):
	""" Retreiving course ID """
	response = session.get(course_link)
	matches = re.search('data-course-id="(\d+)"', response.text, re.IGNORECASE)
	return matches.groups()[0] if matches else None

def get_lecture_indexes(course_id, lecture_start, lecture_end):
	course_url = 'https://www.udemy.com/api-1.1/courses/{0}/curriculum?fields[lecture]=@min,completionRatio,progressStatus&fields[quiz]=@min,completionRatio'.format(course_id)
	html=session.get(course_url).text
	indexes=re.findall('"lectureIndex":(.*?),',html)
	lecture_id=re.findall('lecture\\\/([0-9]*)","public',html)
	out={}
	for i in range(0,len(indexes)):
		out[lecture_id[i]]=indexes[i]
	return out

def get_data_hash(course_id,lecture_id):
	html=session.get("https://www.udemy.com/api-2.0/users/me/subscribed-courses/"+course_id+"/lectures/"+lecture_id+"?video_only=&auto_play=&fields%5Blecture%5D=asset%2Cembed_url&fields%5Basset%5D=asset_type%2Cdownload_urls%2Ctitle&instructorPreviewMode=False").text
	return re.search('\?data\=(.*?)"',html).group(1)

def login(username, password):
	""" Login with popu-page. """
	login_url = 'https://www.udemy.com/join/login-popup/?displayType=ajax&display_type=popup&showSkipButton=1&returnUrlAfterLogin=https%3A%2F%2Fwww.udemy.com%2F&next=https%3A%2F%2Fwww.udemy.com%2F&locale=en_US'
	csrf_token = get_csrf_token()
	payload = {'isSubmitted': 1, 'email': username, 'password': password,
			   'displayType': 'ajax', 'csrfmiddlewaretoken': csrf_token}
	response = session.post(login_url, payload)

	access_token = response.cookies.get('access_token')
	client_id = response.cookies.get('client_id')
	if access_token is None:
		print("Error: Couldn\'t fetch token !")
		sys.exit(1)
	session.set_auth_headers(access_token, client_id)

	response = response.text
	if 'error' in response:
		print(response)
		sys.exit(1)

def get_caption_links(data_value):
  html=session.get("https://www.udemy.com/new-lecture/view/?data="+data_value+"&xdm_e=https%3A%2F%2Fwww.udemy.com%2Fpenetration-testing%2Flearn%2F&xdm_c=default1724&xdm_p=4").text.replace("&amp;","&")
  return re.findall('"captions" src="(.*?)"',html)

login(sys.argv[2],sys.argv[3])
url=sys.argv[1]
course_id=get_course_id(url)
lectures=get_lecture_indexes(course_id,1,50)
os.mkdir("captions")
captions={}

print "Get captions links..."

for i in lectures:
	os.mkdir("captions/Lecture_"+lectures[i])
	for caption in get_caption_links(get_data_hash(course_id,i)):
		captions[caption]=lectures[i]
		sys.stdout.write("\rLecture #"+lectures[i]+": "+caption)
		sys.stdout.flush()

print "Start downloading captions..."

for link in captions:
  try:
    f=open("captions/Lecture_"+captions[link]+"/"+link.split("/")[4].split("?")[0],"w")
    data=requests.get(link).content
    f.write(data)
    f.close()
    sys.stdout.write("\r[OK] "+link.split("/")[4].split("?")[0])
    sys.stdout.flush()
  except:
    print "[CANNOT DOWNLOAD] "+link
