import {render} from '@testing-library/react';
import App from './App';
import {RecoilRoot} from 'recoil';

test('render quay app', () => {
  render(
    <RecoilRoot>
      <App />
    </RecoilRoot>,
  );
});
