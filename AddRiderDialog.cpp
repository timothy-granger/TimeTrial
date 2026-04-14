#include "AddRiderDialog.h"
#include "ui_AddRiderDialog.h"

AddRiderDialog::AddRiderDialog(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::AddRiderDialog)
{
    ui->setupUi(this);

    connect( ui->bibNumber,     SIGNAL( editingFinished() ), SLOT( checkBibNumber()     ) );
    connect( ui->startPosition, SIGNAL( editingFinished() ), SLOT( checkStartPosition() ) );
    connect( ui->lastName,      SIGNAL( editingFinished() ), SLOT( checkLastName()      ) );
    connect( ui->firstName,     SIGNAL( editingFinished() ), SLOT( checkFirstName()     ) );

}

AddRiderDialog::~AddRiderDialog()
{
    delete ui;
}

QString AddRiderDialog::bibNumber( void )
{
    return  ui->bibNumber->text();
}

QString AddRiderDialog::lastName( void )
{
    return ui->lastName->text();
}

QString AddRiderDialog::firstName( void )
{
    return ui->firstName->text();
}

QString AddRiderDialog::category( void )
{
    return ui->category->currentText();
}

int AddRiderDialog::startPosition( void )
{
    return ui->startPosition->text().toInt();
}

void AddRiderDialog::setStartList( QTableWidget *table )
{
    m_startList = table;
}

void AddRiderDialog::setMode( int iMode )
{
    m_iMode = iMode;
}

void AddRiderDialog::setBibNumber( QString   sValue )
{
    m_sBib = sValue;    //  Maintains Value for Edit compare

    ui->bibNumber->setText( sValue );
}

void AddRiderDialog::setLastName ( QString   sValue )
{
    ui->lastName->setText( sValue );
}

void AddRiderDialog::setFirstName( QString   sValue )
{
    ui->firstName->setText( sValue );
}

void AddRiderDialog::setCategory ( QString   sValue )
{
    ui->category->setCurrentText( sValue );
}

void AddRiderDialog::setPosition ( int       iValue )
{
    int     iStart;

    m_iPosition = iValue;

    if ( iValue < 1 )
    {
        iStart      = getNextStart();
    }
    else
    {
        iStart      = iValue;
    }

    ui->startPosition->setText( QString::number( iStart ) );
}

void AddRiderDialog::checkBibNumber( void )
{
    bool        bBibValid = true;

    QString     sLast  = ui->lastName->text();
    QString     sFirst = ui->firstName->text();

    if ( ui->bibNumber->text().isEmpty() )
        bBibValid = false;

    //  Search Start List for Bib #
    for ( int i = 0; ( i < m_startList->rowCount() ) && bBibValid; i++ )
    {
        QTableWidgetItem    *bibItem = m_startList->item( i, 0 );

        if ( ( ui->bibNumber->text().trimmed() == bibItem->text().trimmed() ) && ( ui->bibNumber->text() != m_sBib ) )
            bBibValid = false;
    }

    if ( !bBibValid )
    {
        ui->bibNumber->clear();
        ui->bibNumber->setFocus();

        //  Pop Message!
        qDebug( "Duplicate Bib #!");
    }

    if ( !sLast.isEmpty() && !sFirst.isEmpty() )
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(true);
    }
    else
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(false);
    }
}

void AddRiderDialog::checkStartPosition( void )
{
    bool    bValid = true;
    int     iStart = ui->startPosition->text().toInt();

    QString     sLast  = ui->lastName->text();
    QString     sFirst = ui->firstName->text();

    for ( int i = 0; ( i < m_startList->rowCount() ) && bValid; i++ )
    {
        int iCurrent = m_startList->item( i, 4 )->text().toInt();

        if ( ( iCurrent == iStart ) && ( iStart != m_iPosition ) )
            bValid = false;
    }

    if ( !bValid )
    {
        iStart = getNextStart();

        ui->startPosition->setText( QString::number( iStart ) );
    }

    if ( !sLast.isEmpty() && !sFirst.isEmpty() )
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(true);
    }
    else
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(false);
    }

}

void AddRiderDialog::checkLastName( void )
{
    QString     sLast  = ui->lastName->text();
    QString     sFirst = ui->firstName->text();

    if ( !sLast.isEmpty() && !sFirst.isEmpty() )
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(true);
    }
    else
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(false);
    }

}

void AddRiderDialog::checkFirstName( void )
{
    QString     sLast  = ui->lastName->text();
    QString     sFirst = ui->firstName->text();

    if ( !sLast.isEmpty() && !sFirst.isEmpty() )
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(true);
    }
    else
    {
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(false);
    }

}

int AddRiderDialog::getNextStart( void )
{
    int     iStart = 1;
    bool    bFound = false;

    for ( int i = 0; ( i < m_startList->rowCount() ) && !bFound; i++ )
    {
        int iCurrent = m_startList->item( i, 4 )->text().toInt();

        if ( iCurrent == iStart )
            iStart++;
    }

    return iStart;
}

bool AddRiderDialog::riderEntryValid( void )
{

}

void AddRiderDialog::showEvent(QShowEvent *event)
{
    QString     sBibNumber   = ui->bibNumber->text();
    QString     sLastName    = ui->lastName->text();
    QString     sFirstName   = ui->firstName->text();
    QString     sPosition    = ui->startPosition->text();

    ui->bibNumber->setFocus();

    if ( sBibNumber.isEmpty() || sLastName.isEmpty() || sFirstName.isEmpty() || sPosition.isEmpty() )
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(false);
    else
        ui->buttonBox->button(QDialogButtonBox::Ok)->setEnabled(true);

}
