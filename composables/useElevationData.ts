export interface ElevationPoint {
  distanceKm: number
  elevationM: number
}

export function useElevationData() {
  const { data, pending, error } = useFetch<ElevationPoint[]>('/elevation-data.json', {
    key: 'elevation-profile',
  })

  return { points: data, pending, error }
}
