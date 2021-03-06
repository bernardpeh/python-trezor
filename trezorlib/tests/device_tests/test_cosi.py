# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from hashlib import sha256

from .common import TrezorTest
from trezorlib import cosi

from trezorlib.tools import parse_path


@pytest.mark.skip_t2
class TestCosi(TrezorTest):

    def test_cosi_commit(self):
        self.setup_mnemonic_pin_passphrase()

        digest = sha256(b'this is a message').digest()

        c0 = self.client.cosi_commit(parse_path("10018'/0'"), digest)
        c1 = self.client.cosi_commit(parse_path("10018'/1'"), digest)
        c2 = self.client.cosi_commit(parse_path("10018'/2'"), digest)

        assert c0.pubkey != c1.pubkey
        assert c0.pubkey != c2.pubkey
        assert c1.pubkey != c2.pubkey

        assert c0.commitment != c1.commitment
        assert c0.commitment != c2.commitment
        assert c1.commitment != c2.commitment

        digestb = sha256(b'this is a different message').digest()

        c0b = self.client.cosi_commit(parse_path("10018'/0'"), digestb)
        c1b = self.client.cosi_commit(parse_path("10018'/1'"), digestb)
        c2b = self.client.cosi_commit(parse_path("10018'/2'"), digestb)

        assert c0.pubkey == c0b.pubkey
        assert c1.pubkey == c1b.pubkey
        assert c2.pubkey == c2b.pubkey

        assert c0.commitment != c0b.commitment
        assert c1.commitment != c1b.commitment
        assert c2.commitment != c2b.commitment

    def test_cosi_sign(self):
        self.setup_mnemonic_pin_passphrase()

        digest = sha256(b'this is a message').digest()

        c0 = self.client.cosi_commit(parse_path("10018'/0'"), digest)
        c1 = self.client.cosi_commit(parse_path("10018'/1'"), digest)
        c2 = self.client.cosi_commit(parse_path("10018'/2'"), digest)

        global_pk = cosi.combine_keys([c0.pubkey, c1.pubkey, c2.pubkey])
        global_R = cosi.combine_keys([c0.commitment, c1.commitment, c2.commitment])

        sig0 = self.client.cosi_sign(parse_path("10018'/0'"), digest, global_R, global_pk)
        sig1 = self.client.cosi_sign(parse_path("10018'/1'"), digest, global_R, global_pk)
        sig2 = self.client.cosi_sign(parse_path("10018'/2'"), digest, global_R, global_pk)

        sig = cosi.combine_sig(global_R, [sig0.signature, sig1.signature, sig2.signature])

        cosi.verify(sig, digest, global_pk)

    def test_cosi_compat(self):
        self.setup_mnemonic_pin_passphrase()

        digest = sha256(b'this is not a pipe').digest()
        remote_commit = self.client.cosi_commit(parse_path("10018'/0'"), digest)

        local_privkey = sha256(b'private key').digest()[:32]
        local_pubkey = cosi.pubkey_from_privkey(local_privkey)
        local_nonce, local_commitment = cosi.get_nonce(local_privkey, digest, 42)

        global_pk = cosi.combine_keys([remote_commit.pubkey, local_pubkey])
        global_R = cosi.combine_keys([remote_commit.commitment, local_commitment])

        remote_sig = self.client.cosi_sign(parse_path("10018'/0'"), digest, global_R, global_pk)
        local_sig = cosi.sign_with_privkey(digest, local_privkey, global_pk, local_nonce, global_R)
        sig = cosi.combine_sig(global_R, [remote_sig.signature, local_sig])

        cosi.verify(sig, digest, global_pk)
