import NextAuth, { Account, Profile } from "next-auth"
import GithubProvider from "next-auth/providers/github"
import { PrismaAdapter } from "@next-auth/prisma-adapter"
import prisma from "../../../lib/prisma"
import { JWT } from "next-auth/jwt"

export default NextAuth({
  adapter: PrismaAdapter(prisma),
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID,
      clientSecret: process.env.GITHUB_CLIENT_SECRET,
    }),
  ],
  session: {strategy: "database"},
  callbacks: {
    session: async ({session, user, token}) => {
       session.id = user.id
      return session
    }
  }
})