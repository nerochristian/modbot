import { PrismaClient } from '@prisma/client'
import { PrismaLibSql } from '@prisma/adapter-libsql'
const prisma = new PrismaClient({ adapter: new PrismaLibSql({ url: 'file:./dev.db' }) })
const c = await prisma.case.findUnique({ where: { ref: 1211 }, include: { member: true } })
console.log('case in DB:', c ? `#CASE-${c.ref} "${c.reason}" by ${c.moderator}` : 'NOT FOUND')
console.log('member warnings now:', c?.member.warnings, '(the warn action incremented this)')
console.log('total cases in DB:', await prisma.case.count(), '(was 210 seeded)')
await prisma.$disconnect()
