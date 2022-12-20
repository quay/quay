import {mock} from './MockAxios';

import './data/login/login';

import './data/user/robots';
import './data/user/user';
import './data/repository/security';

import './data/tag/tag';
import './data/tag/labels';
import './data/tag/manifest';

import './data/repository/repository';

import './data/config/config';
import './data/config/logo';

// Order matters here. We match with more specific API endpoints first
import './data/organization/members';
import './data/organization/robots';
import './data/organization/organization';

mock.onAny().passThrough();
