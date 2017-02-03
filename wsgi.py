"""
Coinfee: They make money, you make money
"""

import json
import yaml
import numbers
from pprint import pprint
from urllib2 import urlopen

import bitcoinaddress
import jinja2
import pybitcoin
from datadog import statsd

TIMEOUT = 5

# These should be moved to a json config file

BLOCKCYPHER_API_KEY = 'blockcypher'

WALLET_SECRET = 'justasecret'

# Where we make money.
COINFEE_ADDRESS = '1address'

WALLETAPI = 'https://bitaps.com/api/address/{}'

MINIMUM_SATOSHIS = 10000
MINIMUM_USER_FEE = 10000

OUR_FEE = 11000

MAX_UNIQUE_LENGTH = 64

# Set to descriptive string if true.
DEPRECATED = False

# FIXME: We only send 3 transactions, but it seems like we
# are losing something along the way. Maybe some unaccounted
# fees.
#
# So we waste 1,000 Satoshis for a split request, and 2,000
# for one that isn't. Yucky.
TRANSACTIONS = 3 + 1
TX_FEE = 1000
OUR_TOTAL_FEE = OUR_FEE + TX_FEE * TRANSACTIONS

DEBUG = True


def pulse(metric):
    full_metric = 'coinfee.{}'.format(metric)
    statsd.increment(full_metric)
    debug('Sending stat: {}'.format(full_metric))


def debug(message):
    if DEBUG is True:
        pprint(message)
    return message


def wallet_fatness(address):
    for attempts in [1, 2, 3]:
        http_return = urlopen(WALLETAPI.format(address), timeout=TIMEOUT)
        if http_return.getcode() == 200:
            data = yaml.safe_load(http_return.read())
            for must_have in ['sent', 'balance']:
                if must_have not in data:
                    pulse('wallet_fatness.no_key.{}'.format(must_have))
                    raise
            return (data)
        pulse('wallet_fatness.soft_fail')
    pulse('wallet_fatness.hard_fail')
    return False


def calculate_address_private(data):
    """
    Calculates what the private key should be. Kind of.
    FIXME.
    Doesn't return wif...
    """
    str_data = str(data)
    debug(str_data)
    passphrase = WALLET_SECRET + str_data
    key = pybitcoin.BitcoinPrivateKey.from_passphrase(passphrase=passphrase)
    return key


def calculate_address(data):
    private_key = calculate_address_private(data)
    return private_key.public_key().address()


def application(env, start_response):
    """
    This is where uwsgi calls us.
    """
    def reply(status, data, headers=[]):
        """
        Need to use this as return reply().
        """
        start_response(str(status), headers)
        return data
    print env
    path = env['REQUEST_URI']
    method = env['REQUEST_METHOD']

    # FIXME, remove when auto redirect at uwsgi level is in place.
    scheme = env['wsgi.url_scheme']
    host = env['HTTP_HOST']
    pulse(scheme)

    pulse('hit')

    if 'HTTP_REFERER' in env:
        referer = env['HTTP_REFERER']
        debug('{} to {} from {} referer'.format(method,
                                                path,
                                                referer))
        pulse('hit.has_referer')
    else:
        pulse('hit.no_referer')

    if '..' in path:
        pulse('dotdotinpath')
        return reply(401, '')
    if path.startswith('/static/'):
        if method == 'GET':
            try:
                with open('.' + path) as fp:
                    pulse('static.file.200')
                    return reply(200,
                                 fp.read(),
                                 [('Cache-Control', 'max-age=300')])

            except IOError:
                pulse('static.file.404')
                return reply(404, '')

    if path == '/payment':
        if method == 'POST':
            pulse('payment.hit')
            # http://stackoverflow.com/questions/956867
            # Doing the json dump -> yaml_safeload is supposedly safer,
            # and it gives us the data as a string instead of unicode.
            # If we try to return unicode to uwsgi, it seems to bomb out
            # and return nothing other than the status header to the user.
            try:
                input_json = json.dumps(json.load(env['wsgi.input']))
                data = yaml.safe_load(input_json)
            except:
                pulse('payment.bad_json')
                return reply(400, 'Where\'s your json?')
            response = {'deprecated': DEPRECATED,
                        'status': False,
                        'just_paid': False}
            sanitized_data = {}
            response['satoshis'] = OUR_TOTAL_FEE
            key_list = ['address', 'satoshis', 'unique']
            if 'fee' in data and 'fee_address' in data:
                if 'address' in data:
                    if data['address'] == data['fee_address']:
                        msg = 'Address and fee_address should not be the same.'
                        return reply(400, msg)
                key_list.append('fee')
                key_list.append('fee_address')
                if not isinstance(data['fee'], numbers.Integral):
                    return reply(400, 'Fee must be integer.')
                if data['fee'] < MINIMUM_USER_FEE:
                    return reply(400, 'Fee too small.')
                response['satoshis'] += data['fee']
            for key in key_list:
                if key not in data:
                    return reply(400, '{} not in JSON.'.format(key))
                sanitized_data[key] = data[key]
            if not isinstance(data['unique'], basestring):
                return reply(400, 'unique must be string.')
            if len(data['unique']) > MAX_UNIQUE_LENGTH:
                msg = 'unique must be less than or equal to {}'
                msg = msg.format(MAX_UNIQUE_LENGTH)
                return reply(400, msg)
            if not isinstance(data['satoshis'], numbers.Integral):
                return reply(400, 'satoshis must be integer.')
            if data['satoshis'] < MINIMUM_SATOSHIS:
                return reply(400, 'satoshis must 10,000 or more.')
            response['satoshis'] += data['satoshis']
            for address in ['address', 'fee_address']:
                if address in data:
                    # bitcoinaddress.validate is stupid. It allows Dogecoin
                    # addresses. We make sure it begins with '1'.
                    if bitcoinaddress.validate(data[address]) is False or \
                            data[address][0] != '1':
                        message = '{} is an invalid address.'.format(address)
                        return reply(400, message)
            response['address'] = calculate_address(sanitized_data)
            priv_address = calculate_address_private(sanitized_data).to_hex()
            debug(response['address'])
            overview = wallet_fatness(response['address'])
            if overview is False:
                pulse('yikes_false_overview')
                return reply(500, 'Please try again.')
            sent = overview['sent']
            balance = overview['balance']
            # We do this just in case the user overpays.
            address_satoshis = balance - OUR_TOTAL_FEE
            if 'fee' in sanitized_data:
                address_satoshis -= sanitized_data['fee']
            debug('Balance: {}'.format(str(balance)))
            debug('Sent: {}'.format(str(sent)))
            # Check if we've already paid before.
            if sent != 0:
                response['status'] = True
            elif balance >= response['satoshis']:
                debug('Balance is high enough to pay.')
                blockchain_client = pybitcoin.BlockcypherClient(
                    BLOCKCYPHER_API_KEY)

                def pay_monies(address, satoshis):
                    debug('Paying {} {} Satoshis'.format(address,
                                                         satoshis))
                    return pybitcoin.send_to_address(address,
                                                     satoshis,
                                                     priv_address,
                                                     blockchain_client)

                if 'fee' in data:
                    pulse('payment.has_fee')
                    pay_monies(data['fee_address'],
                               data['fee'])
                else:
                    pulse('payment.has_no_fee')

                pay_monies(data['address'],
                           address_satoshis)
                try:
                    pay_monies(COINFEE_ADDRESS,
                               OUR_FEE)
                except:
                    pulse('payment.pay_self_exception')
                pulse('omg.money')
                response['just_paid'] = True
                response['status'] = True
            return reply(200, json.dumps(response))
        else:
            pulse('payment.405')
            return reply(405, 'Method not allowed')

    if path == '/':
        # FIXME, remove when auto redirect at uwsgi level is in place.
        if scheme != 'https':
            if host == 'coinfee.net':
                pulse('index.http_to_https')
                return reply(301, '', [('Location', 'https://coinfee.net/')])
        pulse('index.hit')
        template = jinja2.Environment(
            loader=jinja2.FileSystemLoader('./')
            ).get_template('index.html')
        return reply(200, str(template.render()))

    pulse('404')
    return reply(404, 'Not found.')
