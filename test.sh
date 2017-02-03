#!/bin/sh

set -e

fail() {
    echo FAIL: $*
    exit 1
}

flake8 wsgi.py

# Negative tests.

echo '{"satoshis": 10000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"lolwut", fee:10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "No 400 for invalid fee address."
echo '{"satoshis": 10000, "unique": "justatest", "address":"lolwut"}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "No 400 for invalid fee address."
echo '{"satoshis": 10000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": 100}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "No 400 for too small of fee."
echo '{"satoshis": 10000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": -10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "No 400 for negative fee."
echo '{"satoshis": 10000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": "lolwut"}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "No 400 for non-integer fee."
echo '{"satoshis": 10000, "unique": "justatest", "address":"D59BzA5DLqaQBey5GUR4xhzAM3a3qGYJyC", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": 10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with Dogecoin address."
echo '{"satoshis": 10000, "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": 10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with missing unique for payment with fee."
echo '{"satoshis": 10000,  "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "satoshis": 10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with missing unique."
# 36 is max unique length.
echo '{"satoshis": 10000, "unique": "12345678901234567890123456789012345678901234567890123456789012345", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq"}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with unique too long."
echo '{"satoshis": 1000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq"}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with satoshis too small."
echo '{"unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq"}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with missing satoshis."
echo '{badjson: 150, "satoshis": 10000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": 10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with bad json."
echo '{"satoshis": 10000, "unique": {}, "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": 10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 400' || fail "Should fail with unique not a string."

# Positive tests.

echo '{"satoshis": 10000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address":"19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": 10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 200' || fail "Unable to create job with fee."
echo '{"satoshis": 10000, "unique": "justatest", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq"}' | curl -si -X POST -d @- localhost:8081/payment | grep -q 'HTTP/1.1 200' || fail "Unable to create job without fee."
echo '{"satoshis": 10000, "unique": "neverbeenpaid", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq"}' | curl -si -X POST -d @- localhost:8081/payment | grep -qF '"status": false' || fail "Unpaid job is paid???"
echo '{"satoshis": 10000, "unique": "alreadypaid", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq"}' | curl -si -X POST -d @- localhost:8081/payment | grep -qF '1CLg5quffs1LipmXq8Vbbc39Twz9NPJyNC' || fail "Job returns wrong address!!!!"
echo '{"satoshis": 10000, "unique": "alreadypaid", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq"}' | curl -si -X POST -d @- localhost:8081/payment | grep -qF '"status": true' || fail "Paid job for 1CLg5quffs1LipmXq8Vbbc39Twz9NPJyNC is unpaid???"
echo '{"satoshis": 10000, "unique": "alreadypaid", "address":"16jCrzcXo2PxadrQiQwUgwrmEwDGQYBwZq", "fee_address": "19x2Phcf3dqYWtfXXWcFu3YqvCQS2rb3Ct", "fee": 10000}' | curl -si -X POST -d @- localhost:8081/payment | grep -qF '"status": true' || fail "Paid job for 18CpRPyMQCsE4KDqanFVQZZnQeJWYsD721 is unpaid???"
