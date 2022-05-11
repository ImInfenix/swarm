import { GetServerSidePropsContext, InferGetServerSidePropsType } from 'next'
import Head from 'next/head'
import { Prisma } from '@prisma/client'
import prisma from '../../lib/prisma'

export default function TicketLayout(props: InferGetServerSidePropsType<typeof getServerSideProps>) {
  if (props.ticket === undefined || props.ticket === null) {
    return null
  }

  return (
    <>
      <h1>Hello {props.ticket.id}</h1>
      Received data is {props.ticket.id}, created at {props.ticket.createdAt} and updated at {props.ticket.updatedAt}
      <h3>{props.ticket.title}</h3>
      <p>{props.ticket.content}</p>
    </>
  )
}

export async function getServerSideProps(context: GetServerSidePropsContext) {
  if (typeof context?.params?.id !== 'string') {
    return { props: {} }
  }

  const idStr: string = context?.params?.id

  if (idStr === undefined) {
    return { props: {} }
  }

  const id: number = parseInt(idStr)
  var ticket: Prisma.PromiseReturnType<typeof prisma.ticket.findUnique> = await prisma.ticket.findUnique({
    where: {
      id: id,
    },
  })

  ticket = JSON.parse(JSON.stringify(ticket))

  return { props: { ticket } }
}
