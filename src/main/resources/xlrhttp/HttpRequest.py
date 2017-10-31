#
# Copyright 2017 XEBIALABS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import re
import urllib

from java.lang import String
from java.util import Arrays

from org.apache.commons.codec.binary import Base64
from org.apache.http import HttpHost
from org.apache.http.auth import AuthScope, NTCredentials
from org.apache.http.client.config import AuthSchemes, RequestConfig
from org.apache.http.client.methods import HttpGet, HttpPost, HttpPut, HttpDelete, HttpPatch
from org.apache.http.client.protocol import HttpClientContext
from org.apache.http.util import EntityUtils
from org.apache.http.entity import StringEntity
from org.apache.http.impl.client import BasicCredentialsProvider, HttpClientBuilder, HttpClients
from org.apache.http.protocol import BasicHttpContext

from com.xebialabs.xlrelease.domain.configuration import HttpConnection

from xlrhttp.HttpResponse import HttpResponse

class HttpRequest:
    def __init__(self, params, username = None, password = None, domain = None):
        """
        Builds an HttpRequest

        :param params: an HttpConnection
        :param username: the username
            (optional, it will override the credentials defined on the HttpConnection object)
        :param password: an password
            (optional, it will override the credentials defined on the HttpConnection object)
        """
        self.params = HttpConnection(params)
        self.shared_domain = params['domain']
        self.username = username
        self.password = password
        self.domain = domain
        self.authentication = params['authenticationMethod']

    def doRequest(self, **options):
        """
        Performs an HTTP Request

        :param options: A keyword arguments object with the following properties :
            method: the HTTP method : 'GET', 'PUT', 'POST', 'DELETE'
                (optional: GET will be used if empty)
            context: the context url
                (optional: the url on HttpConnection will be used if empty)
            body: the body of the HTTP request for PUT & POST calls
                (optional: an empty body will be used if empty)
            contentType: the content type to use
                (optional, no content type will be used if empty)
            headers: a dictionary of headers key/values
                (optional, no headers will be used if empty)
        :return: an HttpResponse instance
        """
        request = self.buildRequest(
            options.get('method', 'GET'),
            options.get('context', ''),
            options.get('body', ''),
            options.get('contentType', None),
            options.get('headers', None))
        return self.executeRequest(request)


    def get(self, context, **options):
        """
        Performs an Http GET Request

        :param context: the context url
        :param options: the options keyword argument described in doRequest()
        :return: an HttpResponse instance
        """
        options['method'] = 'GET'
        options['context'] = context
        return self.doRequest(**options)


    def put(self, context, body, **options):
        """
        Performs an Http PUT Request

        :param context: the context url
        :param body: the body of the HTTP request
        :param options: the options keyword argument described in doRequest()
        :return: an HttpResponse instance
        """
        options['method'] = 'PUT'
        options['context'] = context
        options['body'] = body
        return self.doRequest(**options)


    def post(self, context, body, **options):
        """
        Performs an Http POST Request

        :param context: the context url
        :param body: the body of the HTTP request
        :param options: the options keyword argument described in doRequest()
        :return: an HttpResponse instance
        """
        options['method'] = 'POST'
        options['context'] = context
        options['body'] = body
        return self.doRequest(**options)


    def delete(self, context, **options):
        """
        Performs an Http DELETE Request

        :param context: the context url
        :param options: the options keyword argument described in doRequest()
        :return: an HttpResponse instance
        """
        options['method'] = 'DELETE'
        options['context'] = context
        return self.doRequest(**options)

    def patch(self, context, body, **options):
        """
        Performs an Http PATCH Request

        :param context: the context url
        :param body: the body of the HTTP request
        :param options: the options keyword argument described in doRequest()
        :return: an HttpResponse instance
        """
        options['method'] = 'PATCH'
        options['context'] = context
        options['body'] = body
        return self.doRequest(**options)

    def buildRequest(self, method, context, body, contentType, headers):
        url = self.quote(self.createPath(self.params.getUrl(), context))

        method = method.upper()

        if method == 'GET':
            request = HttpGet(url)
        elif method == 'POST':
            request = HttpPost(url)
            request.setEntity(StringEntity(body))
        elif method == 'PUT':
            request = HttpPut(url)
            request.setEntity(StringEntity(body))
        elif method == 'DELETE':
            request = HttpDelete(url)
        elif method == 'PATCH':
            request = HttpPatch(url)
            request.setEntity(StringEntity(body))
        else:
            raise Exception('Unsupported method: ' + method)

        request.addHeader('Content-Type', contentType)
        request.addHeader('Accept', contentType)
        self.setProxy(request)
        self.setHeaders(request, headers)

        return request


    def createPath(self, url, context):
        url = re.sub('/*$', '', url)
        if context is None:
            return url
        elif context.startswith('/'):
            return url + context
        else:
            return url + '/' + context

    def quote(self, url):
        return urllib.quote(url, ':/?&=%')


    def set_basic_credentials(self, request):
        credentials = self.get_credentials()
        encoding = Base64.encodeBase64String(String(credentials["username"] + ':' + credentials["password"]).getBytes())
        request.addHeader('Authorization', 'Basic ' + encoding)

    def get_ntlm_client(self):
        request_config = RequestConfig.custom().setTargetPreferredAuthSchemes(Arrays.asList(AuthSchemes.NTLM)).build()
        httpclient = HttpClients.custom().setDefaultRequestConfig(request_config).build()
        return httpclient

    def get_credentials(self):
        if self.username:
            username = self.username
            password = self.password
            domain = self.domain
        elif self.params.getUsername():
            username = self.params.getUsername()
            password = self.params.getPassword()
            domain = self.shared_domain
        else:
            return
        return {'username': username, 'password':password, 'domain':domain}

    def setProxy(self, request):
        if not self.params.getProxyHost():
            return

        proxy = HttpHost(self.params.getProxyHost(), int(self.params.getProxyPort()))
        config = RequestConfig.custom().setProxy(proxy).build()
        request.setConfig(config)


    def setHeaders(self, request, headers):
        if headers:
            for key in headers:
                request.setHeader(key, headers[key])


    def executeRequest(self, request):
        client = None
        response = None
        try:
            local_context = BasicHttpContext()
            if self.authentication == "Ntlm":
                credentials = self.get_credentials()
                client = self.get_ntlm_client()
                credentials_provider = BasicCredentialsProvider()
                credentials_provider.setCredentials(AuthScope.ANY, NTCredentials(credentials["username"], credentials["password"], None, credentials["domain"]))
                local_context.setAttribute(HttpClientContext.CREDS_PROVIDER, credentials_provider)
            else:
                client = HttpClients.createDefault()
                self.set_basic_credentials(request)

            response = client.execute(request, local_context)
            status = response.getStatusLine().getStatusCode()
            entity = response.getEntity()
            result = EntityUtils.toString(entity, "UTF-8") if entity else None
            headers = response.getAllHeaders()
            EntityUtils.consume(entity)

            return HttpResponse(status, result, headers)
        finally:
            if response:
                response.close()
            if client:
                client.close()
