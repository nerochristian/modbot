import { createContext, useContext } from 'react'

export const GuildContext = createContext(null)

export function useGuild() {
  return useContext(GuildContext)
}
