// SHOW OLD WEBSITE
// SHOW MULTIPLE CALLS TO EXPLAIN WHY USE CACHE
// SHOW REACT HOOKS

const axios = require('axios');

(async () => {
  for (let i = 1000; i < 3000; i++) {
    await axios.post(
      'http://localhost:8080/api/v1/organization/',
      {
        email: 'organization-' + i + '@gmail.com',
        name: 'organization-' + i,
      },
      {
        credentials: 'include',
        headers: {
          'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:106.0) Gecko/20100101 Firefox/106.0',
          Accept: 'application/json, text/plain, */*',
          'Accept-Language': 'en-US,en;q=0.5',
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json',
          'X-CSRF-Token':
            'a1JfYi1RmJ6swBOysMv5KY20hEV88foUgrKkqwYvcSayPvkaN_75F_aXz0yCRGsN',
          'Sec-Fetch-Dest': 'empty',
          'Sec-Fetch-Mode': 'cors',
          'Sec-Fetch-Site': 'same-site',
          Cookie:
            '__stripe_mid=31f1e8d7-278d-4222-bb2e-0300ac007e66ab30b9; _csrf_token=.eJw1z8tqwlAUheFXCWds4Ox9bjsZtlRB0RZ7oY7CuWqwJm0SI1Z891pKh_9k8a0Lq3zfpWpo97FhJbMwT5sa1oe57k93j-d-OarFBvnu4Y0ota_bbrH_Om1G_2zPT-PeriqjppV9_-bn-_WsX7EJq1IX-x0rh-4Yb1WH2ywEiq5IMbnCCOnJclBKm8IbC9ZJMEpTCGjRhGRiQqDokzIUMAUuUXIZPE8FWINcRCek9OoW2gORTiiVAZu4csIJoQFQSS-t0ASkuRVkflmfsTvYJjbDP-2j3dZNNdSHyMoLy36d066eZEDZqh0z5IgZYCmh5CabLV_YdcKOfez-LnnvSCv0eSKyudRK5E5LytFLxUUhpArIrj-ZZWau.Y3d_uQ.xglRztGUAtRM8pLnhnuezp069y0; quay.loggedin=true; PGADMIN_LANGUAGE=en; pga4_session=1a098b9a-18f4-4209-82e4-dcdaba8d3e73!68h7VeWCYcGzJtZK6K4f7g3mJ9BjovTrQCDMBS3e0oU=',
        },
        referrer: 'http://127.0.0.1:9000/',
        mode: 'cors',
      },
    );
    for (let j = 0; j < 10; j++) {
      await axios.post(
        'http://localhost:8080/api/v1/repository',
        {
          namespace: 'organization-' + i,
          visibility: 'public',
          repository: 'repository-' + j,
          description: 'Hello World',
          repo_kind: 'image',
        },
        {
          credentials: 'include',
          headers: {
            'User-Agent':
              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:106.0) Gecko/20100101 Firefox/106.0',
            Accept: 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
            'X-CSRF-Token':
              'a1JfYi1RmJ6swBOysMv5KY20hEV88foUgrKkqwYvcSayPvkaN_75F_aXz0yCRGsN',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            Cookie:
              '__stripe_mid=31f1e8d7-278d-4222-bb2e-0300ac007e66ab30b9; _csrf_token=.eJw1z8tqwlAUheFXCWds4Ox9bjsZtlRB0RZ7oY7CuWqwJm0SI1Z891pKh_9k8a0Lq3zfpWpo97FhJbMwT5sa1oe57k93j-d-OarFBvnu4Y0ota_bbrH_Om1G_2zPT-PeriqjppV9_-bn-_WsX7EJq1IX-x0rh-4Yb1WH2ywEiq5IMbnCCOnJclBKm8IbC9ZJMEpTCGjRhGRiQqDokzIUMAUuUXIZPE8FWINcRCek9OoW2gORTiiVAZu4csIJoQFQSS-t0ASkuRVkflmfsTvYJjbDP-2j3dZNNdSHyMoLy36d066eZEDZqh0z5IgZYCmh5CabLV_YdcKOfez-LnnvSCv0eSKyudRK5E5LytFLxUUhpArIrj-ZZWau.Y3d_uQ.xglRztGUAtRM8pLnhnuezp069y0; quay.loggedin=true; PGADMIN_LANGUAGE=en; pga4_session=1a098b9a-18f4-4209-82e4-dcdaba8d3e73!68h7VeWCYcGzJtZK6K4f7g3mJ9BjovTrQCDMBS3e0oU=',
          },
          referrer: 'http://127.0.0.1:9000/',
          mode: 'cors',
        },
      );
    }
  }
})();

// await fetch('http://localhost:8080/api/v1/organization/', {
//   credentials: 'include',
//   headers: {
//     'User-Agent':
//       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:107.0) Gecko/20100101 Firefox/107.0',
//     Accept: 'application/json, text/plain, */*',
//     'Accept-Language': 'en-US,en;q=0.5',
//     'X-Requested-With': 'XMLHttpRequest',
//     'Content-Type': 'application/json',
//     'X-CSRF-Token':
//       'a1JfYi1RmJ6swBOysMv5KY20hEV88foUgrKkqwYvcSayPvkaN_75F_aXz0yCRGsN',
//     'Sec-Fetch-Dest': 'empty',
//     'Sec-Fetch-Mode': 'cors',
//     'Sec-Fetch-Site': 'same-site',
//   },
//   referrer: 'http://localhost:9000/',
//   body: '{"name":"trhee","email":"jon@gmail.com"}',
//   method: 'POST',
//   mode: 'cors',
// });
