import styles from "../styles/TicketsSummary.module.css"

export default function TicketsSummary(props: { ticketCount: number }) {
  return (
    <div className={styles.ticketsSummary}>
      <h3>Tickets summary</h3>

      <p>Total number of tickets {props.ticketCount}</p>
    </div>
  )
}