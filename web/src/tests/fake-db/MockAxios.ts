import axios from 'axios';
// eslint-disable-next-line import/no-extraneous-dependencies
import MockAdapter from 'axios-mock-adapter';

export const mock = new MockAdapter(axios);
