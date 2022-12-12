import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

export interface IPlan {
  hasSubscription: boolean;
  isExistingCustomer: boolean;
  plan: string;
  usedPrivateRepos: number;
}

// FIXME we have to mock this for now

export async function fetchPlan(name: string, isUserOrganization: boolean) {
  // let fetchPlanUrl: string;
  // if (isUserOrganization) {
  //   fetchPlanUrl = `/api/v1/user/${name}/plan`;
  // } else {
  //   fetchPlanUrl = `/api/v1/organization/${name}/plan`;
  // }

  // // TODO: Add return type
  // const response: AxiosResponse = await axios.get(fetchPlanUrl);
  // assertHttpCode(response.status, 200);

  return {
    hasSubscription: true,
    isExistingCustomer: true,
    plan: 'free',
    usedPrivateRepos: 10,
  } as IPlan;
}
