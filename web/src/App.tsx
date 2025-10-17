import {Suspense} from 'react';
import {BrowserRouter, Route, Routes} from 'react-router-dom';

import 'src/App.css';

import {LoadingPage} from 'src/components/LoadingPage';
import {useAnalytics} from 'src/hooks/UseAnalytics';
import {Signin} from 'src/routes/Signin/Signin';
import {CreateAccount} from 'src/routes/CreateAccount/CreateAccount';
import UpdateUser from 'src/routes/UpdateUser/UpdateUser';
import {OAuthCallbackHandler} from 'src/routes/OAuthCallback/OAuthCallbackHandler';
import {OAuthError} from 'src/routes/OAuthCallback/OAuthError';
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
              <Route path="/signin" element={<Signin />} />
              <Route path="/createaccount" element={<CreateAccount />} />
              <Route path="/updateuser" element={<UpdateUser />} />
              <Route path="/oauth-error" element={<OAuthError />} />
              <Route
                path="/oauth2/:provider/callback/*"
                element={<OAuthCallbackHandler />}
              />
              <Route path="/*" element={<StandaloneMain />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}
