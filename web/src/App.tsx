import {Suspense} from 'react';
import {BrowserRouter, Route, Routes} from 'react-router-dom';

import 'src/App.css';

import {LoadingPage} from 'src/components/LoadingPage';
import {useAnalytics} from 'src/hooks/UseAnalytics';
import {Signin} from 'src/routes/Signin/Signin';
import {CreateAccount} from 'src/routes/CreateAccount/CreateAccount';
import {StandaloneMain} from 'src/routes/StandaloneMain';
import {ThemeProvider} from './contexts/ThemeContext';

export default function App() {
  useAnalytics();

  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <Suspense fallback={<LoadingPage />}>
            <Routes>
              <Route path="/*" element={<StandaloneMain />} />
              <Route path="/signin" element={<Signin />} />
              <Route path="/createaccount" element={<CreateAccount />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}
