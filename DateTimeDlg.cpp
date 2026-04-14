#include "DateTimeDlg.h"
#include "ui_DateTimeDlg.h"

DateTimeDlg::DateTimeDlg(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::DateTimeDlg)
{
    ui->setupUi(this);
}

DateTimeDlg::~DateTimeDlg()
{
    delete ui;
}

void DateTimeDlg::setDateTime( QDateTime dateTime )
{
    ui->dateTimeEdit->setDateTime( dateTime );
}
void DateTimeDlg::setMinimumDateTime( QDateTime qMin )
{
    ui->dateTimeEdit->setMinimumDateTime( qMin );
}

void DateTimeDlg::setMaximumDateTime( QDateTime qMax )
{
    ui->dateTimeEdit->setMaximumDateTime( qMax );
}

void DateTimeDlg::setLabel( QString sLabel )
{
    ui->dateTimeLabel->setText( sLabel );
}

QDateTime DateTimeDlg::dateTime( void )
{
    return ui->dateTimeEdit->dateTime();
}
