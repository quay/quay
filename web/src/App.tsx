import {Suspense} from 'react';
import {BrowserRouter, Route, Routes} from 'react-router-dom';

import 'src/App.css';

import {LoadingPage} from 'src/components/LoadingPage';
import {useAnalytics} from 'src/hooks/UseAnalytics';
import {Signin} from 'src/routes/Signin/Signin';
import {StandaloneMain} from 'src/routes/StandaloneMain';
import {ThemeProvider} from './contexts/ThemeContext';
import { InitPlugins } from "../../artifacts/plugins_base";

export default function App() {
  useAnalytics();
  InitPlugins();

  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <Suspense fallback={<LoadingPage />}>
            <Routes>
              <Route path="/*" element={<StandaloneMain />} />
              <Route path="/signin" element={<Signin />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}
