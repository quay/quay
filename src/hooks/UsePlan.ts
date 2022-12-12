import {fetchPlan} from 'src/resources/PlanResource';
import {useQuery} from '@tanstack/react-query';
import {useOrganization} from './UseOrganization';

export function usePlan(name: string) {
  // Get usernames
  const {isUserOrganization} = useOrganization(name);

  // Get organization plan
  const {
    data: plan,
    isLoading,
    error,
    isPlaceholderData,
  } = useQuery(['organization', name, 'plan'], () => {
    return fetchPlan(name, isUserOrganization);
  });

  return {
    error,
    loading: isLoading || isPlaceholderData,
    plan,
  };
}
